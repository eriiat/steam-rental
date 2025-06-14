# 创建 add_test_account.py 文件
from account_manager import AccountManager

mgr = AccountManager()
# mgr.add_account(
#     username="eriiat66",
#     password="Nanchen00",
#     shared_secret="ZU0mnkqktuLChK00Oy9822MHJuE="  # 示例TOTP密钥
# )

print(mgr.add_game("双影奇境"))
print(mgr.add_game("inZOI"))
# print(len('gAAAAABoP-leV5wAZBbWix5xcXcWuo_aD5jWRGly60zoJBYmRV6wBpac3wlmnOF7C-G-WqGnEa_DF3jW8KFHa7q2P27NK5YHIg=='))
print(mgr.add_account(
    username="eriiat66",
    password="Nanchen00",
    shared_secret="ZU0mnkqktuLChK00Oy9822MHJuE=",  # 示例TOTP密钥
    game_names=["双影奇境","inZOI"]
))

print(mgr.update_account_games(1,["双影奇境","鹅鸭杀"]))
print(mgr.get_accounts())
print(mgr.get_accounts_by_game("双影奇境"))
# print(mgr.delete_account(1))