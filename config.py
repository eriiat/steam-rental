import os


class Config:
    # MySQL配置
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'eriiat'
    MYSQL_PASSWORD = 'qesd2341*D531'
    MYSQL_DB = 'steam_rental'

    # 加密密钥
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uA4iUin6Wqb6McAzmp7llMltDizj7McACkvcrlGnQTU'
    ENCRYPTION_KEY = b'b5SgGYyCdBhgt2qmd3WXGWePN58oUY7ltKRSMByeeFc='  # 32字节密钥

    # 管理员凭据
    ADMIN_USER = 'admin'
    ADMIN_PASS = 'admin123'

    # 应用设置
    MAX_ACCESS = 100
    RENTAL_DAYS = 1  # 默认租赁天数
