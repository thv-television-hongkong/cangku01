from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
import binascii

# 生成RSA密钥对
key = RSA.generate(2048)
private_key = key.export_key()
public_key = key.publickey().export_key()

# 签名函数
def rsa_sign(message, private_key):
    # 转换私钥为RSA对象
    priv_key = RSA.import_key(private_key)
    # 计算消息哈希
    hash_obj = SHA256.new(message.encode('utf-8'))
    # 使用私钥签名
    signer = pkcs1_15.new(priv_key)
    signature = signer.sign(hash_obj)
    return binascii.hexlify(signature).decode('utf-8')

# 验证函数
def rsa_verify(message, signature, public_key):
    # 转换公钥为RSA对象
    pub_key = RSA.import_key(public_key)
    # 计算消息哈希
    hash_obj = SHA256.new(message.encode('utf-8'))
    # 转换签名字符串为字节
    signature_bytes = binascii.unhexlify(signature.encode('utf-8'))
    # 使用公钥验证
    verifier = pkcs1_15.new(pub_key)
    try:
        verifier.verify(hash_obj, signature_bytes)
        return True
    except ValueError:
        return False

message = "Alice pays Bob 10 BTC"
# 生成签名
signature = rsa_sign(message, private_key)
print(f"签名: {signature}")
# 验证签名
is_valid = rsa_verify(message, signature, public_key)
print(f"签名验证结果: {is_valid}")
