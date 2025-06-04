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

    def create_order(self, order_id, customer_contact, rental_days=Config.RENTAL_DAYS):
        """创建新订单"""
        conn = self.get_connection()
        try:
            # 获取可用账号
            account = self.get_available_account()

            if not account:
                return False, "没有可用账号"

            with conn.cursor() as cursor:
                start_time = datetime.now()
                expire_time = start_time + timedelta(days=rental_days)

                sql = """
                INSERT INTO orders 
                (order_id, account_id, customer_contact, start_time, expire_time)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    order_id,
                    account['account_id'],
                    customer_contact,
                    start_time,
                    expire_time
                ))
                conn.commit()
                return True, account['account_id']
        except Exception as e:
            print(f"创建订单失败: {str(e)}")
            return False, str(e)
        finally:
            conn.close()

    def get_available_account(self):
        """获取可用账号"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 获取最近未使用的可用账号
                sql = """
                SELECT * FROM steam_accounts 
                WHERE is_active = TRUE 
                AND account_id NOT IN (
                    SELECT account_id FROM orders 
                    WHERE expire_time > %s AND status = 'active'
                )
                ORDER BY last_used ASC 
                LIMIT 1
                """
                cursor.execute(sql, (datetime.now(),))
                account = cursor.fetchone()

                if account:
                    # 解密部分信息
                    account['steam_username'] = self.account_mgr.decrypt_data(account['steam_username'])
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
                    order['steam_username'] = self.account_mgr.decrypt_data(order['steam_username'])
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