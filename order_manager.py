import pymysql
from config import Config
from account_manager import AccountManager
from datetime import datetime, timedelta


class OrderManager:
    def __init__(self):
        self.account_mgr = AccountManager()

    def get_connection(self):
        return pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            db=Config.MYSQL_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    def create_order(self, order_id,game_name, customer_contact, rental_days=Config.RENTAL_DAYS):
        """创建新订单（不设置开始时间）"""
        conn = self.get_connection()
        try:
            # 获取可用账号
            account = self.get_available_account(game_name)
            if not account:
                return False, "没有可用账号"

            with conn.cursor() as cursor:
                sql = """
                INSERT INTO orders 
                (order_id, account_id, customer_contact, rental_days, status)
                VALUES (%s, %s, %s, %s, 'pending')
                """
                cursor.execute(sql, (
                    order_id,
                    account['account_id'],
                    customer_contact,
                    rental_days
                ))
                conn.commit()
                return True, account['account_id']
        except Exception as e:
            print(f"创建订单失败: {str(e)}")
            return False, str(e)
        finally:
            conn.close()

    def update_order_expiry(self, order_id, new_expire_days):
        """更新订单有效期"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 获取订单当前信息
                cursor.execute("SELECT start_time, expire_time, rental_days, status FROM orders WHERE order_id = %s",
                               (order_id,))
                result = cursor.fetchone()

                if not result:
                    return False, "未找到订单"

                # 如果订单尚未激活（pending状态）
                if result['status'] == 'pending':
                    # 只更新租赁天数
                    update_sql = "UPDATE orders SET rental_days = %s WHERE order_id = %s"
                    cursor.execute(update_sql, (new_expire_days, order_id))
                    conn.commit()
                    return True, f"订单租赁天数已更新为 {new_expire_days} 天（将在首次使用时生效）"

                # 如果订单已激活
                current_expire = result['expire_time']
                if current_expire < datetime.now():
                    new_expire_time = datetime.now() + timedelta(days=new_expire_days)
                else:
                    new_expire_time = current_expire + timedelta(days=new_expire_days)

                update_sql = "UPDATE orders SET expire_time = %s WHERE order_id = %s"
                cursor.execute(update_sql, (new_expire_time, order_id))
                conn.commit()

                return True, new_expire_time
        except Exception as e:
            print(f"更新订单有效期失败: {str(e)}")
            return False, str(e)
        finally:
            conn.close()

    def update_order_status(self, order_id, new_status):
        """更新订单状态"""
        if new_status not in ['active', 'disabled', 'completed']:
            return False, "无效的状态值"

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                update_sql = """
                UPDATE orders 
                SET status = %s 
                WHERE order_id = %s
                """
                cursor.execute(update_sql, (new_status, order_id))
                conn.commit()

                if cursor.rowcount > 0:
                    return True, "订单状态更新成功"
                return False, "未找到指定订单"
        except Exception as e:
            print(f"更新订单状态失败: {str(e)}")
            return False, str(e)
        finally:
            conn.close()

    def get_available_account(self, game_name):
        """获取指定游戏的可用账号"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 获取最近未使用的可用账号（按最后使用时间升序）
                sql = """
                SELECT sa.* 
                FROM steam_accounts sa
                INNER JOIN account_games ag ON sa.account_id = ag.account_id
                INNER JOIN games g ON ag.game_id = g.game_id
                WHERE g.game_name = %s 
                  AND sa.is_active = TRUE 
                  AND sa.account_id NOT IN (
                      SELECT account_id 
                      FROM orders 
                      WHERE status = 'active' OR status = 'pending'
                  )
                ORDER BY sa.last_used ASC 
                LIMIT 1
                """
                cursor.execute(sql, (game_name,))
                account = cursor.fetchone()

                if account:
                    # 解密密码（共享密钥保持加密状态）
                    account['steam_password'] = self.account_mgr.decrypt_data(account['steam_password'])
                return account
        finally:
            conn.close()

    def get_orders(self):
        """获取所有订单"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT o.*, a.steam_username 
                FROM orders o
                JOIN steam_accounts a ON o.account_id = a.account_id
                ORDER BY o.created_at DESC
                """
                cursor.execute(sql)
                orders = cursor.fetchall()

                # 解密账号信息
                for order in orders:
                    order['steam_username'] = order['steam_username']
                return orders
        finally:
            conn.close()

    def expire_orders(self):
        """将过期订单标记为过期状态"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                UPDATE orders 
                SET status = 'expired' 
                WHERE expire_time < %s 
                AND status = 'active'
                """
                cursor.execute(sql, (datetime.now(),))
                conn.commit()
                return cursor.rowcount
        finally:
            conn.close()