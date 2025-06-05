import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()
class Config:
    # ===== MySQL 配置 =====
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '123456')
    MYSQL_DB = os.getenv('MYSQL_DB', 'steam_rental')

    # ===== 加密密钥 =====
    SECRET_KEY = os.getenv('SECRET_KEY', 'uA4iUin6Wqb6McAzmp7llMltDizj7McACkvcrlGnQTU')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'b5SgGYyCdBhgt2qmd3WXGWePN58oUY7ltKRSMByeeFc=')

    # ===== 管理员账号 =====
    ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
    ADMIN_PASS = os.getenv('ADMIN_PASS', 'admin123')

    # ===== 应用设置 =====
    MAX_ACCESS = int(os.getenv('MAX_ACCESS', 100))
    RENTAL_DAYS = int(os.getenv('RENTAL_DAYS', 1))