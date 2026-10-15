from ecdsa import SigningKey, VerifyingKey, NIST256p  # 使用NIST推荐的P-256曲线
import hashlib

def generate_ecdsa_keypair():
    """生成ECDSA密钥对（私钥+公钥）"""
    private_key = SigningKey.generate(curve=NIST256p)  # 生成私钥
    public_key = private_key.get_verifying_key()        # 从私钥导出公钥
    return private_key, public_key

def sign_message(private_key, message, user_info):
    """
    使用私钥对消息签名（嵌入个人信息）
    :param private_key: 私钥对象
    :param message: 待签名的原始消息（字符串）
    :param user_info: 个人信息（字典，包含name、student_id）
    :return: 签名结果（字节流）
    """
    # 拼接消息+个人信息，确保签名包含身份标识
    signed_content = f"{message}\n个人信息：姓名={user_info['name']}，身份证={user_info['id']}".encode()
    # 使用SHA-256哈希后签名
    signature = private_key.sign(signed_content, hashfunc=hashlib.sha256)
    return signature, signed_content

def verify_signature(public_key, signature, signed_content):
    """
    使用公钥验证签名
    :param public_key: 公钥对象
    :param signature: 签名结果（字节流）
    :param signed_content: 已签名的内容（含个人信息，字节流）
    :return: 验证结果（True/False）
    """
    try:
        public_key.verify(signature, signed_content, hashfunc=hashlib.sha256)
        return True
    except:
        return False

if __name__ == "__main__":
    # 1. 生成密钥对
    private_key, public_key = generate_ecdsa_keypair()
    print("=== 密钥对生成完成 ===")
    print(f"私钥（Hex）：{private_key.to_string().hex()}")
    print(f"公钥（Hex）：{public_key.to_string().hex()}\n")

    # 2. 配置个人信息和待签名消息
    user_info = {
        "name": "XXX",    # 替换为你的姓名
        "id": "XXX"  # 替换为你的id
    }
    original_message = "这是一个测试消息，用于ECDSA签名验证"

    # 3. 对消息签名（嵌入个人信息）
    signature, signed_content = sign_message(private_key, original_message, user_info)
    print("=== 签名结果 ===")
    print(f"已签名内容：\n{signed_content.decode()}")
    print(f"签名（Hex）：{signature.hex()}\n")

    # 4. 验证签名
    is_valid = verify_signature(public_key, signature, signed_content)
    print("=== 签名验证结果 ===")
    print(f"验证结果：{'成功 ✅' if is_valid else '失败 ❌'}")