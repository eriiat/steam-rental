
import pyotp
totp = pyotp.TOTP('ZU0mnkqktuLChK00Oy9822MHJuE=')
auth_code = totp.now()
print(auth_code)