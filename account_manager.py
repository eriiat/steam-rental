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

    def add_account(self, username, password, shared_secret):
        """添加新Steam账号"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                enc_username = self.encrypt_data(username)
                enc_password = self.encrypt_data(password)
                print(enc_username)
                print(enc_password)
                sql = """
                INSERT INTO steam_accounts 
                (steam_username, steam_password, steam_shared_secret)
                VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (enc_username, enc_password, shared_secret))
                conn.commit()
                return True
        except Exception as e:
            print(f"添加账号失败: {str(e)}")
            return False
        finally:
            conn.close()

    def get_accounts(self):
        """获取所有账号"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM steam_accounts"
                cursor.execute(sql)
                accounts = cursor.fetchall()

                # 解密账号信息
                for account in accounts:
                    account['steam_username'] = self.decrypt_data(account['steam_username'])
                    # 密码不显示明文
                    account['password_set'] = "是" if account['steam_password'] else "否"
                return accounts
        finally:
            conn.close()

    def update_account_status(self, account_id, is_active):
        """更新账号状态"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "UPDATE steam_accounts SET is_active = %s WHERE account_id = %s"
                cursor.execute(sql, (is_active, account_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"更新账号状态失败: {str(e)}")
            return False
        finally:
            conn.close()