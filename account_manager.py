import pymysql
from config import Config
from cryptography.fernet import Fernet
from datetime import datetime


class AccountManager:
    def __init__(self):
        self.cipher = Fernet(Config.ENCRYPTION_KEY)

    def get_connection(self):
        return pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            db=Config.MYSQL_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    def encrypt_data(self, data):
        """加密敏感数据"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data):
        """解密数据"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    # 新增方法：添加游戏到数据库
    def add_game(self, game_name):
        """添加新游戏到数据库"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "INSERT IGNORE INTO games (game_name) VALUES (%s)"
                cursor.execute(sql, (game_name,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"添加游戏失败: {str(e)}")
            return False
        finally:
            conn.close()

    # 修改方法：添加账号并关联游戏
    def add_account(self, username, password, shared_secret, game_names=None):
        """添加新Steam账号并关联游戏"""
        if game_names is None:
            game_names = []

        conn = self.get_connection()
        try:
            conn.autocommit(False)  # 开启事务

            with conn.cursor() as cursor:
                # 加密账号信息
                enc_username = username
                enc_password = self.encrypt_data(password)

                # 插入账号
                sql_account = """
                INSERT INTO steam_accounts 
                (steam_username, steam_password, steam_shared_secret)
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql_account, (enc_username, enc_password, shared_secret))
                account_id = cursor.lastrowid

                # 关联游戏
                if game_names:
                    # 确保游戏存在
                    for game_name in set(game_names):  # 去重
                        if game_name.strip():  # 非空检查
                            # 插入游戏（如果不存在）
                            sql_game = "INSERT IGNORE INTO games (game_name) VALUES (%s)"
                            cursor.execute(sql_game, (game_name,))

                            # 获取游戏ID
                            sql_get_id = "SELECT game_id FROM games WHERE game_name = %s"
                            cursor.execute(sql_get_id, (game_name,))
                            game = cursor.fetchone()

                            if game:
                                # 创建关联
                                sql_link = """
                                INSERT IGNORE INTO account_games 
                                (account_id, game_id) 
                                VALUES (%s, %s)
                                """
                                cursor.execute(sql_link, (account_id, game['game_id']))

                conn.commit()
                return account_id  # 返回新创建的账号ID
        except Exception as e:
            print(f"添加账号失败: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.autocommit(True)  # 恢复自动提交
            conn.close()

    # 新增方法：获取账号关联的游戏
    def get_account_games(self, account_id):
        """获取账号关联的游戏列表"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT g.game_name 
                FROM account_games ag
                JOIN games g ON ag.game_id = g.game_id
                WHERE ag.account_id = %s
                """
                cursor.execute(sql, (account_id,))
                return [game['game_name'] for game in cursor.fetchall()]
        finally:
            conn.close()

    # 新增方法：更新账号游戏关联
    def update_account_games(self, account_id, password=None, shared_secret=None, is_active=None, new_games=None):
        """更新账号关联的游戏、密码、共享密钥和状态"""
        if new_games is None:
            new_games = []

        conn = self.get_connection()
        try:
            conn.autocommit(False)
            with conn.cursor() as cursor:
                # 构建账号更新语句
                updates = []
                params = []

                # 如果提供了新密码且不为空，则更新密码
                if password is not None and password.strip() != "":
                    enc_password = self.encrypt_data(password)
                    updates.append("steam_password = %s")
                    params.append(enc_password)

                # 更新共享密钥（如果提供）
                if shared_secret is not None:
                    updates.append("steam_shared_secret = %s")
                    params.append(shared_secret)

                # 更新状态（如果提供）
                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)

                # 添加最后更新时间
                updates.append("last_used = %s")
                params.append(datetime.now())

                # 如果有需要更新的字段
                if updates:
                    sql_account = f"""
                    UPDATE steam_accounts 
                    SET {', '.join(updates)}
                    WHERE account_id = %s
                    """
                    params.append(account_id)
                    cursor.execute(sql_account, tuple(params))

                # 更新游戏关联
                # 删除现有关联
                sql_delete = "DELETE FROM account_games WHERE account_id = %s"
                cursor.execute(sql_delete, (account_id,))

                # 添加新关联
                for game_name in set(new_games):
                    if game_name.strip():
                        # 确保游戏存在
                        sql_game = "INSERT IGNORE INTO games (game_name) VALUES (%s)"
                        cursor.execute(sql_game, (game_name,))

                        # 获取游戏ID
                        sql_get_id = "SELECT game_id FROM games WHERE game_name = %s"
                        cursor.execute(sql_get_id, (game_name,))
                        game = cursor.fetchone()

                        if game:
                            sql_link = """
                            INSERT INTO account_games 
                            (account_id, game_id) 
                            VALUES (%s, %s)
                            """
                            cursor.execute(sql_link, (account_id, game['game_id']))

                conn.commit()
                return True
        except Exception as e:
            print(f"更新账号信息失败: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.autocommit(True)
            conn.close()

    # 修改方法：获取账号详情（包含游戏信息）
    def get_accounts(self, with_games=False):
        """获取所有账号（可选包含游戏信息）"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM steam_accounts"
                cursor.execute(sql)
                accounts = cursor.fetchall()

                # 解密账号信息
                for account in accounts:
                    # 用户名未加密，直接使用
                    account['steam_username'] = account['steam_username']
                    account['password_set'] = "是" if account['steam_password'] else "否"

                    # 获取关联游戏
                    if with_games:
                        account['games'] = self.get_account_games(account['account_id'])

                return accounts
        finally:
            conn.close()

    # 新增方法：通过游戏查找账号
    def get_accounts_by_game(self, game_name):
        """通过游戏名称查找关联账号"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT sa.* 
                FROM steam_accounts sa
                JOIN account_games ag ON sa.account_id = ag.account_id
                JOIN games g ON ag.game_id = g.game_id
                WHERE g.game_name = %s
                """
                cursor.execute(sql, (game_name,))
                accounts = cursor.fetchall()

                # 解密账号信息
                for account in accounts:
                    account['steam_username'] = account['steam_username']
                    account['password_set'] = "是" if account['steam_password'] else "否"
                    account['games'] = self.get_account_games(account['account_id'])

                return accounts
        finally:
            conn.close()

    # 新增方法：删除账号
    def delete_account(self, account_id):
        """删除Steam账号及其关联数据"""
        conn = self.get_connection()
        try:
            conn.autocommit(False)

            with conn.cursor() as cursor:
                # 1. 删除账号-游戏关联
                sql_delete_games = "DELETE FROM account_games WHERE account_id = %s"
                cursor.execute(sql_delete_games, (account_id,))

                # 2. 删除账号本身
                sql_delete_account = "DELETE FROM steam_accounts WHERE account_id = %s"
                cursor.execute(sql_delete_account, (account_id,))

                # 3. 检查是否有订单关联此账号
                sql_check_orders = "SELECT COUNT(*) AS order_count FROM orders WHERE account_id = %s"
                cursor.execute(sql_check_orders, (account_id,))
                result = cursor.fetchone()

                if result['order_count'] > 0:
                    # 有订单关联，不能删除，回滚
                    conn.rollback()
                    return {
                        'success': False,
                        'message': '无法删除账号，因为存在关联的订单'
                    }

                conn.commit()
                return {
                    'success': True,
                    'message': '账号删除成功'
                }

        except Exception as e:
            print(f"删除账号失败: {str(e)}")
            conn.rollback()
            return {
                'success': False,
                'message': f'删除账号失败: {str(e)}'
            }
        finally:
            conn.autocommit(True)
            conn.close()

    # 新增方法：更新账号基本信息
    def update_account(self, account_id, username=None, password=None, shared_secret=None, is_active=None):
        """更新Steam账号基本信息"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 构建更新语句
                updates = []
                params = []

                if username is not None:
                    updates.append("steam_username = %s")
                    params.append(username)

                if password is not None:
                    # 密码需要加密
                    enc_password = self.encrypt_data(password)
                    updates.append("steam_password = %s")
                    params.append(enc_password)

                if shared_secret is not None:
                    updates.append("steam_shared_secret = %s")
                    params.append(shared_secret)

                if is_active is not None:
                    updates.append("is_active = %s")
                    params.append(is_active)

                # 如果没有更新字段，直接返回
                if not updates:
                    return False

                # 添加最后更新时间
                updates.append("last_used = %s")
                params.append(datetime.now())

                # 构建SQL语句
                sql = f"""
                UPDATE steam_accounts 
                SET {', '.join(updates)}
                WHERE account_id = %s
                """
                params.append(account_id)

                # 执行更新
                cursor.execute(sql, tuple(params))
                conn.commit()

                return cursor.rowcount > 0

        except Exception as e:
            print(f"更新账号失败: {str(e)}")
            return False
        finally:
            conn.close()

    # 新增方法：获取单个账号详情
    def get_account(self, account_id):
        """获取单个账号的详细信息"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                SELECT * 
                FROM steam_accounts 
                WHERE account_id = %s
                """
                cursor.execute(sql, (account_id,))
                account = cursor.fetchone()

                if account:
                    # 获取关联游戏
                    account['games'] = self.get_account_games(account_id)
                    return account
                return None
        finally:
            conn.close()

    # 新增方法：检查账号是否可用
    def check_account_available(self, account_id):
        """检查账号是否可用（未被租用）"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 检查是否有活跃订单
                sql = """
                SELECT COUNT(*) AS active_orders 
                FROM orders 
                WHERE account_id = %s 
                  AND status = 'active' 
                  AND expire_time > NOW()
                """
                cursor.execute(sql, (account_id,))
                result = cursor.fetchone()

                # 检查账号本身是否激活
                sql_account = """
                SELECT is_active 
                FROM steam_accounts 
                WHERE account_id = %s
                """
                cursor.execute(sql_account, (account_id,))
                account = cursor.fetchone()

                return result['active_orders'] == 0 and account['is_active'] == 1
        finally:
            conn.close()

    def get_all_games(self):
        """获取所有游戏"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM games"
                cursor.execute(sql)
                games = cursor.fetchall()

                # 解密账号信息
                for game in games:
                    # 用户名未加密，直接使用
                    game['game_name'] = game['game_name']

                return games
        finally:
            conn.close()