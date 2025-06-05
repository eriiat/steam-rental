import hmac
import base64
import hashlib
import time


def generate_steam_guard_code(shared_secret: str) -> str:
    """
    生成Steam令牌验证码
    :param shared_secret: Base64编码的共享密钥
    :return: 5位验证码字符串
    """
    # Steam使用的自定义字母表（去除了易混淆字符）
    steam_alphabet = '23456789BCDFGHJKMNPQRTVWXY'

    # 1. 解码Base64共享密钥
    secret = base64.b64decode(shared_secret)

    # 2. 计算当前时间步（30秒一个周期）
    timestamp = int(time.time())
    time_step = timestamp // 30

    # 3. 将时间步转换为8字节大端序
    time_bytes = time_step.to_bytes(8, 'big')

    # 4. 使用HMAC-SHA1生成哈希
    hmac_hash = hmac.new(secret, time_bytes, hashlib.sha1).digest()

    # 5. 动态截取哈希片段
    offset = hmac_hash[-1] & 0x0F
    code_bytes = hmac_hash[offset:offset + 4]

    # 6. 转换为整数并移除符号位
    full_code = int.from_bytes(code_bytes, 'big') & 0x7FFFFFFF

    # 7. 生成5位验证码
    code = ''
    for _ in range(5):
        full_code, index = divmod(full_code, len(steam_alphabet))
        code = steam_alphabet[index] + code

    return code[::-1]