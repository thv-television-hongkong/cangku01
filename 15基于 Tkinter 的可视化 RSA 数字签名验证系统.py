import tkinter as tk
from tkinter import messagebox, scrolledtext
import rsa
import hashlib
import base64
from datetime import datetime
import os


class RSASignatureApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🔐 数字签名验证系统 - RSA实验")
        self.root.geometry("900x700")
        self.root.configure(bg='#f0f0f0')

        # 初始化RSA密钥
        self.public_key = None
        self.private_key = None
        self.generated_keys = False

        # 创建界面
        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        # 标题
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        title_frame.pack(fill=tk.X, padx=10, pady=10)

        title_label = tk.Label(title_frame, text="🔐 数字签名验证系统",
                               font=("Arial", 24, "bold"), fg='white', bg='#2c3e50')
        title_label.pack(pady=20)

        # 主框架
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 左侧：密钥生成
        key_frame = tk.LabelFrame(main_frame, text="🔑 RSA密钥生成",
                                  font=("Arial", 12, "bold"), bg='#f0f0f0')
        key_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.setup_key_generation(key_frame)

        # 右侧：签名与验证
        sign_frame = tk.LabelFrame(main_frame, text="✍️ 签名与验证",
                                   font=("Arial", 12, "bold"), bg='#f0f0f0')
        sign_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        self.setup_signature_verification(sign_frame)

        # 底部：日志区域
        log_frame = tk.LabelFrame(self.root, text="📋 操作日志",
                                  font=("Arial", 12, "bold"), bg='#f0f0f0')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8,
                                                  font=("Courier", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def setup_key_generation(self, parent):
        """设置密钥生成界面"""
        # 密钥长度选择
        length_frame = tk.Frame(parent, bg='#f0f0f0')
        length_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(length_frame, text="密钥长度:", bg='#f0f0f0').pack(side=tk.LEFT)
        self.key_length = tk.IntVar(value=2048)
        tk.Radiobutton(length_frame, text="1024位", variable=self.key_length,
                       value=1024, bg='#f0f0f0').pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(length_frame, text="2048位", variable=self.key_length,
                       value=2048, bg='#f0f0f0').pack(side=tk.LEFT, padx=5)

        # 生成密钥按钮
        generate_btn = tk.Button(parent, text="🔄 生成RSA密钥对",
                                 command=self.generate_keys,
                                 bg='#3498db', fg='white', font=("Arial", 10, "bold"))
        generate_btn.pack(pady=10)
        # 密钥显示区域
        key_display_frame = tk.Frame(parent, bg='#f0f0f0')
        key_display_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 公钥显示
        public_frame = tk.LabelFrame(key_display_frame, text="公钥", bg='#f0f0f0')
        public_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.public_text = tk.Text(public_frame, height=8, width=40,
                                   wrap=tk.WORD, font=("Courier", 8))
        self.public_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 私钥显示
        private_frame = tk.LabelFrame(key_display_frame, text="私钥", bg='#f0f0f0')
        private_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.private_text = tk.Text(private_frame, height=8, width=40,
                                    wrap=tk.WORD, font=("Courier", 8))
        self.private_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

  # 保存密钥按钮
        save_key_frame = tk.Frame(parent, bg='#f0f0f0')
        save_key_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(save_key_frame, text="💾 保存公钥", command=self.save_public_key,
                  bg='#27ae60', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(save_key_frame, text="💾 保存私钥", command=self.save_private_key,
                  bg='#e74c3c', fg='white').pack(side=tk.LEFT, padx=5)

    def setup_signature_verification(self, parent):
        """设置签名验证界面"""
        # 消息输入
        msg_frame = tk.LabelFrame(parent, text="📝 待签名消息", bg='#f0f0f0')
        msg_frame.pack(fill=tk.X, padx=10, pady=5)

        self.message_entry = tk.Text(msg_frame, height=4, width=40,
                                     font=("Arial", 10))
        self.message_entry.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 签名操作
        sign_frame = tk.Frame(parent, bg='#f0f0f0')
        sign_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(sign_frame, text="✍️ 生成签名", command=self.generate_signature,
                  bg='#9b59b6', fg='white', font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # 签名显示
        signature_frame = tk.LabelFrame(parent, text="🔏 数字签名", bg='#f0f0f0')
        signature_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.signature_text = tk.Text(signature_frame, height=6, width=40,
                                      wrap=tk.WORD, font=("Courier", 8))
        self.signature_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 验证操作
        verify_frame = tk.Frame(parent, bg='#f0f0f0')
        verify_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(verify_frame, text="🔍 验证签名", command=self.verify_signature,
                  bg='#f39c12', fg='white', font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # 验证结果显示
        self.verify_result = tk.Label(parent, text="等待验证...",
                                      bg='#ecf0f1', fg='#7f8c8d',
                                      font=("Arial", 12, "bold"))
        self.verify_result.pack(fill=tk.X, padx=10, pady=10)

        # 快速测试按钮
        test_frame = tk.Frame(parent, bg='#f0f0f0')
        test_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(test_frame, text="🚀 快速测试", command=self.quick_test,
                  bg='#1abc9c', fg='white', font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def generate_keys(self):
        """生成RSA密钥对"""
        try:
            self.log_message("开始生成RSA密钥对...")
            self.root.config(cursor="watch")
            self.root.update()

            # 生成密钥对
            key_size = self.key_length.get()
            (self.public_key, self.private_key) = rsa.newkeys(key_size)

            # 显示密钥
            self.public_text.delete(1.0, tk.END)
            self.public_text.insert(tk.END, self.public_key.save_pkcs1().decode())

            self.private_text.delete(1.0, tk.END)
            self.private_text.insert(tk.END, self.private_key.save_pkcs1().decode())

            self.generated_keys = True
            self.log_message(f"成功生成{key_size}位RSA密钥对！")

            self.root.config(cursor="")

        except Exception as e:
            self.log_message(f"密钥生成失败: {str(e)}")
            messagebox.showerror("错误", f"密钥生成失败: {str(e)}")
            self.root.config(cursor="")

    def save_public_key(self):
        """保存公钥到文件"""
        if not self.generated_keys:
            messagebox.showwarning("警告", "请先生成密钥对！")
            return

        try:
            filename = f"public_key_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pem"
            with open(filename, 'wb') as f:
                f.write(self.public_key.save_pkcs1())
            self.log_message(f"公钥已保存到: {filename}")
            messagebox.showinfo("成功", f"公钥已保存到: {filename}")

        except Exception as e:
            self.log_message(f"保存公钥失败: {str(e)}")
            messagebox.showerror("错误", f"保存公钥失败: {str(e)}")

    def save_private_key(self):
        """保存私钥到文件"""
        if not self.generated_keys:
            messagebox.showwarning("警告", "请先生成密钥对！")
            return

        try:
            filename = f"private_key_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pem"
            with open(filename, 'wb') as f:
                f.write(self.private_key.save_pkcs1())
            self.log_message(f"私钥已保存到: {filename}")
            messagebox.showinfo("成功", f"私钥已保存到: {filename}")
        except Exception as e:
            self.log_message(f"保存私钥失败: {str(e)}")
            messagebox.showerror("错误", f"保存私钥失败: {str(e)}")

    def generate_signature(self):
        """生成数字签名"""
        if not self.generated_keys:
            messagebox.showwarning("警告", "请先生成密钥对！")
            return

        message = self.message_entry.get(1.0, tk.END).strip()
        if not message:
            messagebox.showwarning("警告", "请输入要签名的消息！")
            return

        try:
            # 对消息进行哈希
            message_hash = hashlib.sha256(message.encode()).digest()

            # 使用私钥签名
            signature = rsa.sign(message.encode(), self.private_key, 'SHA-256')

            # 显示签名（Base64编码）
            signature_b64 = base64.b64encode(signature).decode()
            self.signature_text.delete(1.0, tk.END)
            self.signature_text.insert(tk.END, signature_b64)

            self.log_message("成功生成数字签名！")

        except Exception as e:
            self.log_message(f"签名生成失败: {str(e)}")
            messagebox.showerror("错误", f"签名生成失败: {str(e)}")

    def verify_signature(self):
        """验证数字签名"""
        if not self.generated_keys:
            messagebox.showwarning("警告", "请先生成密钥对！")
            return

        message = self.message_entry.get(1.0, tk.END).strip()
        signature_b64 = self.signature_text.get(1.0, tk.END).strip()

        if not message or not signature_b64:
            messagebox.showwarning("警告", "请输入消息和签名！")
            return

        try:
            # 解码签名
            signature = base64.b64decode(signature_b64)

            # 验证签名
            try:
                rsa.verify(message.encode(), signature, self.public_key)
                self.verify_result.config(text="✅ 签名验证成功！消息未被篡改。",
                                          bg='#2ecc71', fg='white')
                self.log_message("签名验证成功！")
            except rsa.VerificationError:
                self.verify_result.config(text="❌ 签名验证失败！消息可能被篡改。",
                                          bg='#e74c3c', fg='white')
                self.log_message("签名验证失败！")

        except Exception as e:
            self.log_message(f"签名验证出错: {str(e)}")
            messagebox.showerror("错误", f"签名验证出错: {str(e)}")

    def quick_test(self):
        """快速测试功能"""
        if not self.generated_keys:
            messagebox.showwarning("警告", "请先生成密钥对！")
            return

        # 自动填充测试消息
        test_message = "这是RSA数字签名实验的测试消息！\n发送者：学生A\n时间：" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.message_entry.delete(1.0, tk.END)
        self.message_entry.insert(tk.END, test_message)

        # 生成签名
        self.generate_signature()

        self.log_message("快速测试完成！点击'验证签名'测试验证功能。")

        messagebox.showinfo("快速测试", "测试消息已填充并生成签名！\n点击'验证签名'测试验证功能。")

def main():
    """主函数"""
    root = tk.Tk()
    app = RSASignatureApp(root)

    # 添加实验说明
    welcome_msg = """
🎓 欢迎来到RSA数字签名实验！

📋 实验步骤：
1. 🔑 生成RSA密钥对（可选择1024或2048位）
2. 📝 输入要签名的消息
3. ✍️ 使用私钥生成数字签名
4. 🔍 使用公钥验证签名

🔍 实验目标：
- 理解RSA加密和签名的原理
- 体验数字签名的完整流程
- 学习如何验证消息完整性

💡 提示：使用"快速测试"按钮可以自动完成测试流程！
"""

    # 显示欢迎消息
    messagebox.showinfo("实验说明", welcome_msg)
    app.log_message("实验系统启动成功！")

    root.mainloop()


if __name__ == "__main__":
    main()
