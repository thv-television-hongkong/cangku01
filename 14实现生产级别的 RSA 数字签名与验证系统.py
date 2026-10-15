import rsa
import hashlib


# 生成RSA密钥对（公钥用于验签，私钥用于签名）
def generate_rsa_keys(key_size=2048):
    (public_key, private_key) = rsa.newkeys(key_size)
    return public_key, private_key


# 对数据进行RSA签名（私钥签名）
def rsa_sign(data, private_key, hash_alg="sha256"):
    """
    :param data: 待签名的原始数据（字符串/字节串）
    :param private_key: RSA私钥对象
    :param hash_alg: 哈希算法（sha1/sha256/sha512，需与hashlib属性一致）
    :return: 十六进制格式的签名结果
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    # 直接使用hashlib的属性名，避免连字符问题
    hash_func = getattr(hashlib, hash_alg)()
    hash_func.update(data)
    data_hash = hash_func.digest()

    # rsa.sign的第三个参数需要传标准算法名（带连字符），做映射转换
    alg_map = {
        "sha1": "SHA-1",
        "sha256": "SHA-256",
        "sha512": "SHA-512"
    }
    signature = rsa.sign(data_hash, private_key, alg_map[hash_alg])
    return signature.hex()


# 验证RSA签名（公钥验签）
def rsa_verify(data, signature_hex, public_key, hash_alg="sha256"):
    """
    :param data: 原始数据（字符串/字节串）
    :param signature_hex: 十六进制格式的签名
    :param public_key: RSA公钥对象
    :param hash_alg: 签名使用的哈希算法（sha1/sha256/sha512）
    :return: 验签结果（True/False）
    """
    try:
        if isinstance(data, str):
            data = data.encode("utf-8")
        signature = bytes.fromhex(signature_hex)

        alg_map = {
            "sha1": "SHA-1",
            "sha256": "SHA-256",
            "sha512": "SHA-512"
        }
        rsa.verify(data, signature, public_key)
        return True
    except rsa.VerificationError:
        return False


# 对文件进行签名（适用于大文件）
def sign_file(file_path, private_key, hash_alg="sha256"):
    with open(file_path, "rb") as f:
        hash_func = getattr(hashlib, hash_alg)()
        while chunk := f.read(4096):
            hash_func.update(chunk)
        file_hash = hash_func.digest()

    alg_map = {
        "sha1": "SHA-1",
        "sha256": "SHA-256",
        "sha512": "SHA-512"
    }
    signature = rsa.sign(file_hash, private_key, alg_map[hash_alg])
    return signature.hex()


# 验证文件签名
def verify_file(file_path, signature_hex, public_key, hash_alg="sha256"):
    try:
        with open(file_path, "rb") as f:
            hash_func = getattr(hashlib, hash_alg)()
            while chunk := f.read(4096):
                hash_func.update(chunk)
            file_hash = hash_func.digest()

        signature = bytes.fromhex(signature_hex)
        rsa.verify(file_hash, signature, public_key)
        return True
    except (rsa.VerificationError, FileNotFoundError):
        return False


# 测试主程序
if __name__ == "__main__":
    # 1. 生成RSA密钥对
    pub_key, priv_key = generate_rsa_keys()
    print("✅ RSA密钥对生成完成")

    # 2. 对文本数据签名并验证
    original_data = "BLOCKCHAIN_RSA_SIGNATURE_SYSTEM"
    print(f"\n原始数据: {original_data}")

    # 私钥签名
    signature = rsa_sign(original_data, priv_key)
    print(f"数字签名: {signature[:50]}...（省略部分）")

    # 公钥验签（正常数据）
    verify_result = rsa_verify(original_data, signature, pub_key)
    print(f"数据未篡改 - 验签结果: {verify_result}")

    # 篡改数据后验签
    tampered_data = "BLOCKCHAIN_RSA_SIGNATURE_SYSTEM_TAMPERED"
    tamper_verify = rsa_verify(tampered_data, signature, pub_key)
    print(f"数据被篡改 - 验签结果: {tamper_verify}")

    # 3. 对文件签名并验证（需先创建测试文件）
    test_file = "test_sign_file.txt"
    # 写入测试内容
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(original_data)

    # 文件签名
    file_signature = sign_file(test_file, priv_key)
    print(f"\n文件签名: {file_signature[:50]}...（省略部分）")

    # 验证文件签名
    file_verify = verify_file(test_file, file_signature, pub_key)
    print(f"文件未篡改 - 验签结果: {file_verify}")

    # 篡改文件后验签
    with open(test_file, "a", encoding="utf-8") as f:
        f.write("_TAMPERED")
    tamper_file_verify = verify_file(test_file, file_signature, pub_key)
    print(f"文件被篡改 - 验签结果: {tamper_file_verify}")