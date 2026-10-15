import rsa

# 整合原generate_keys功能：生成RSA密钥对（返回可直接用于加解密的格式）
def generate_keys():
    # 生成2048位RSA密钥对
    (pubkey, privkey) = rsa.newkeys(2048)
    # 提取公钥的e、n和私钥的d、n（适配原加密解密函数）
    public_key = (pubkey.e, pubkey.n)
    private_key = (privkey.d, privkey.n)
    return public_key, private_key

# RSA加密函数（保持原逻辑）
def rsa_encrypt(p_message, p_public_key):
    e, n = p_public_key
    rsa_encrypted = [pow(ord(char), e, n) for char in p_message]
    return rsa_encrypted

# RSA解密函数（保持原逻辑）
def rsa_decrypt(p_encrypted, p_private_key):
    d, n = p_private_key
    rsa_decrypted = ''.join([chr(pow(block, d, n)) for block in p_encrypted])
    return rsa_decrypted

# 测试代码
if __name__ == "__main__":
    message = "BLOCKCHAIN"
    # 生成密钥对
    public_key, private_key = generate_keys()
    # 加密和解密
    encrypted = rsa_encrypt(message, public_key)
    decrypted = rsa_decrypt(encrypted, private_key)
    # 输出结果
    print(f"原始消息: {message}")
    print(f"加密结果: {encrypted}")
    print(f"解密结果: {decrypted}")