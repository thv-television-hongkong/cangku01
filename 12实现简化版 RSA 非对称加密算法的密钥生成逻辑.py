from sympy import randprime, mod_inverse
import math

def generate_keys(bit_size=16):
    # 生成小质数（教学用，实际需更大）
    p = randprime(2 ** (bit_size // 2 - 1), 2 ** (bit_size // 2))
    q = randprime(2 ** (bit_size // 2 - 1), 2 ** (bit_size // 2))
    n = p * q
    phi_n = (p - 1) * (q - 1)

    # 选择公钥e（常用65537，需与phi_n互质）
    e = 65537
    while math.gcd(e, phi_n) != 1:
        e = randprime(2, phi_n - 1)

    # 计算私钥d
    d = mod_inverse(e, phi_n)

    public_key = (e, n)
    private_key = (d, n)
    return public_key, private_key

# 测试生成密钥
public_key, private_key = generate_keys()
print(f"公钥 (e, n): {public_key}")
print(f"私钥 (d, n): {private_key}")