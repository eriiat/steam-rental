# 创建 add_test_account.py 文件
from account_manager import AccountManager

mgr = AccountManager()
# mgr.add_account(
#     username="eriiat66",
#     password="Nanchen00",
#     shared_secret="ZU0mnkqktuLChK00Oy9822MHJuE="  # 示例TOTP密钥
# )

c = mgr.get_accounts()
# print(len('gAAAAABoP-leV5wAZBbWix5xcXcWuo_aD5jWRGly60zoJBYmRV6wBpac3wlmnOF7C-G-WqGnEa_DF3jW8KFHa7q2P27NK5YHIg=='))
print("测试账号添加成功!")
print(c)