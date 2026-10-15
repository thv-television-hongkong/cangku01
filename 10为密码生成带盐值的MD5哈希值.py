import os
import hashlib

def generate_salted_hash(password):
    salt = os.urandom(16)
    salted_password = password.encode('UTF-8') + salt
    hash_md5 = hashlib.md5(salted_password).hexdigest
    return salt.hex(),hash_md5  #返回盐的十六进制和哈希值

password = "user123"
salt,hashed_pwd = generate_salted_hash(password)
print(f"Salt:{salt},Hashed Password:{hashed_pwd}")