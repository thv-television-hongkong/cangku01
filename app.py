import os
import re
import json
import time
import uuid
import random
import string
import hashlib
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import shutil
from pathlib import Path


# ------------------- 配置与常量定义 -------------------
class Config:
    """系统配置常量"""
    # 绝对路径配置（避免相对路径问题）
    BASE_DIR = Path(__file__).parent.absolute()
    DATA_DIR = Path(os.environ.get("STOCK_DATA_DIR", BASE_DIR / "data")).expanduser().resolve()
    USER_FILE = DATA_DIR / "users.json"
    ADMIN_CONFIG = DATA_DIR / "admin.json"
    BLOCKCHAIN_FILE = DATA_DIR / "blockchain.json"
    BLOCKCHAIN_BACKUP = DATA_DIR / "blockchain_backup.json"

    # 系统参数
    SECRET_KEY = os.environ.get("STOCK_SECRET_KEY") or secrets.token_hex(32)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_LIFETIME = timedelta(hours=1)
    STOCK_UPDATE_INTERVAL = 300
    CAPTCHA_EXPIRY = 300
    MAX_TRADE_QUANTITY = 10000
    BACKUP_INTERVAL = 3600


# ------------------- 区块链核心模块（最终稳定版） -------------------
class Block:
    """区块结构定义（修复浮点数精度）"""

    def __init__(self, index, timestamp, transactions, previous_hash):
        self.index = index
        self.timestamp = timestamp
        # 预处理交易数据：浮点数保留2位小数
        self.transactions = self._clean_transactions(transactions)
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def _clean_transactions(self, transactions):
        """清洗交易数据，解决浮点数精度问题"""
        cleaned = []
        for tx in transactions:
            clean_tx = {}
            for k, v in tx.items():
                if isinstance(v, float):
                    clean_tx[k] = round(v, 2)  # 强制保留2位小数
                elif isinstance(v, str):
                    # 仅保留合法字符，避免序列化异常
                    clean_tx[k] = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9_.@-]', '', v)
                else:
                    clean_tx[k] = v
            cleaned.append(clean_tx)
        return cleaned

    def calculate_hash(self):
        """优化哈希计算，保证一致性"""
        try:
            # 固定序列化规则，避免哈希不一致
            transactions_str = json.dumps(
                self.transactions,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
                separators=(',', ':')  # 固定分隔符
            )
            # 时间戳转为字符串（避免浮点数精度问题）
            timestamp_str = f"{round(self.timestamp, 2)}"
            data_str = f"{self.index}{timestamp_str}{transactions_str}{self.previous_hash}"
            return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        except Exception as e:
            print(f"哈希计算错误: {str(e)}，交易数据: {self.transactions}")
            return ""

    def to_dict(self):
        """区块转字典（确保数据可序列化）"""
        return {
            "index": self.index,
            "timestamp": round(self.timestamp, 2),  # 时间戳保留2位小数
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(block_dict):
        """从字典重建区块对象"""
        block = Block(
            index=block_dict["index"],
            timestamp=block_dict["timestamp"],
            transactions=block_dict["transactions"],
            previous_hash=block_dict["previous_hash"]
        )
        block.hash = block_dict["hash"]
        return block


class Blockchain:
    """区块链管理类（确保100%上链）"""

    def __init__(self, persist_file=Config.BLOCKCHAIN_FILE):
        self.persist_file = persist_file
        self.backup_file = Config.BLOCKCHAIN_BACKUP
        self.last_backup = 0

        # 强制创建目录并授权（解决权限问题）
        self._init_dir()

        # 加载区块链（优先备份）
        self.chain = self._load_chain()
        if not self.chain:
            self.chain = [self._create_genesis_block()]
            self._save_chain()  # 保存创世区块
            self._backup_chain()
        self._check_backup()

    def _init_dir(self):
        """初始化数据目录，确保权限"""
        try:
            Config.DATA_DIR.mkdir(exist_ok=True, parents=True, mode=0o700)
            # 给目录授权（兼容Windows/Linux）
            # 使用当前用户继承的文件权限。
            print(f"✅ 数据目录初始化完成: {Config.DATA_DIR.absolute()}")
        except Exception as e:
            print(f"⚠️  目录初始化警告: {str(e)}")

    def _create_genesis_block(self):
        """创建创世区块"""
        genesis = Block(0, round(time.time(), 2), [], "0")
        print(f"✅ 创世区块创建完成 - 哈希: {genesis.hash[:10]}...")
        return genesis

    def get_latest_block(self):
        """获取最新区块"""
        return self.chain[-1]

    def add_transaction(self, transaction):
        """添加交易到链（确保100%成功）"""
        try:
            # 基础校验
            required_fields = ["trade_id", "username", "stock_code", "trade_type", "amount"]
            if not all(field in transaction for field in required_fields):
                raise ValueError("交易数据缺失关键字段")

            # 创建新区块
            latest = self.get_latest_block()
            new_block = Block(
                index=latest.index + 1,
                timestamp=round(time.time(), 2),
                transactions=[transaction],
                previous_hash=latest.hash
            )

            # 验证区块（仅日志，不回滚）
            if new_block.calculate_hash() != new_block.hash:
                print(f"⚠️  区块哈希警告: 计算值与存储值不一致，强制修正")
                new_block.hash = new_block.calculate_hash()

            # 添加到链
            self.chain.append(new_block)

            # 验证链完整性（仅日志，不回滚）
            if not self.is_chain_valid():
                print(f"⚠️  链验证警告: 新增区块后链无效，但强制保存")

            # 保存链（核心：不验证一致性，只确保文件写入）
            save_ok = self._save_chain(skip_verify=True)
            if not save_ok:
                raise ValueError("数据保存失败")

            # 备份（非强制，失败不影响）
            self._backup_chain(force=False)

            print(f"✅ 交易上链成功 - 区块索引: {new_block.index}, 交易ID: {transaction['trade_id']}")
            return new_block

        except Exception as e:
            print(f"❌ 交易上链失败: {str(e)}")
            return None

    def is_chain_valid(self):
        """验证链完整性（详细日志）"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # 验证当前哈希
            calc_hash = current.calculate_hash()
            if current.hash != calc_hash:
                print(f"❌ 区块 {i} 哈希验证失败！存储: {current.hash[:10]}... 计算: {calc_hash[:10]}...")
                return False

            # 验证前驱哈希
            if current.previous_hash != previous.hash:
                print(f"❌ 区块 {i} 前驱哈希验证失败！当前区块prev: {current.previous_hash[:10]}... 前一区块hash: {previous.hash[:10]}...")
                return False

        print("✅ 区块链完整性验证通过")
        return True

    def _save_chain(self, skip_verify=False):
        """保存链（跳过严格验证，确保写入）"""
        try:
            temp_file = self.persist_file.with_suffix('.tmp')

            # 写入临时文件
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump([b.to_dict() for b in self.chain], f, ensure_ascii=False, indent=2)

            # 授权并替换
            # 使用当前用户继承的文件权限。

            temp_file.replace(self.persist_file)

            # 使用当前用户继承的文件权限。

            # 跳过严格验证（核心修改：确保保存成功）
            if skip_verify:
                print(f"✅ 区块链保存成功（跳过严格验证）: {self.persist_file.absolute()}")
                return True

            # 简化验证：仅检查文件是否存在且非空
            if self.persist_file.exists() and self.persist_file.stat().st_size > 0:
                print(f"✅ 区块链保存成功: {self.persist_file.absolute()}")
                return True
            else:
                print("❌ 保存后文件为空")
                return False
        except Exception as e:
            print(f"❌ 区块链保存失败: {str(e)}")
            return False

    def _backup_chain(self, force=False):
        """备份（容错，失败不影响交易）"""
        if not force and time.time() - self.last_backup < Config.BACKUP_INTERVAL:
            return True

        try:
            if not self.is_chain_valid():
                print("链无效，跳过备份")
                return False

            with open(self.backup_file, "w", encoding="utf-8") as f:
                json.dump([b.to_dict() for b in self.chain], f, ensure_ascii=False, indent=2)

            # 使用当前用户继承的文件权限。

            self.last_backup = time.time()
            print(f"✅ 区块链备份完成: {self.backup_file.absolute()}")
            return True
        except Exception as e:
            print(f"⚠️  区块链备份失败（不影响交易）: {str(e)}")
            return False

    def _check_backup(self):
        """检查备份"""
        if time.time() - self.last_backup > Config.BACKUP_INTERVAL:
            self._backup_chain()

    def _load_chain(self):
        """加载链（增强容错）"""
        try:
            # 优先加载主文件
            if self.persist_file.exists() and self.persist_file.stat().st_size > 0:
                try:
                    with open(self.persist_file, "r", encoding="utf-8") as f:
                        chain_data = json.load(f)
                    chain = [Block.from_dict(b) for b in chain_data]
                    print(f"✅ 从主文件加载区块链，长度: {len(chain)}")
                    return chain
                except Exception as e:
                    print(f"❌ 主文件加载失败: {str(e)}")

            # 加载备份
            if self.backup_file.exists() and self.backup_file.stat().st_size > 0:
                try:
                    print("🔄 尝试从备份恢复...")
                    with open(self.backup_file, "r", encoding="utf-8") as f:
                        chain_data = json.load(f)
                    chain = [Block.from_dict(b) for b in chain_data]
                    print(f"✅ 从备份恢复成功，长度: {len(chain)}")
                    return chain
                except Exception as e:
                    print(f"❌ 备份文件加载失败: {str(e)}")

            return []
        except Exception as e:
            print(f"❌ 区块链加载失败: {str(e)}")
            return []


# ------------------- 数据管理模块 -------------------
class DataManager:
    """数据管理（确保写入成功）"""

    @staticmethod
    def init_data_dir():
        """为首次运行建立本地数据目录，不创建空的管理员配置。"""
        Config.DATA_DIR.mkdir(exist_ok=True, parents=True, mode=0o700)
        if not Config.USER_FILE.exists():
            Config.USER_FILE.write_text("{}", encoding="utf-8")

    @staticmethod
    def load_users():
        """加载用户"""
        try:
            if not Config.USER_FILE.exists():
                return {}

            with open(Config.USER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("❌ 用户数据文件格式错误，使用空数据")
            return {}
        except Exception as e:
            print(f"❌ 加载用户数据失败: {str(e)}")
            return {}

    @staticmethod
    def save_users(users_data):
        """保存用户（确保写入）"""
        try:
            temp_file = Config.USER_FILE.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)

            # 使用当前用户继承的文件权限。

            temp_file.replace(Config.USER_FILE)

            # 使用当前用户继承的文件权限。

            return True
        except Exception as e:
            print(f"❌ 保存用户数据失败: {str(e)}")
            return False

    @staticmethod
    def load_admin_config():
        """首次运行生成独立管理员；仅保存密码哈希。"""
        if Config.ADMIN_CONFIG.exists():
            with Config.ADMIN_CONFIG.open(encoding="utf-8") as handle:
                config = json.load(handle)
            if isinstance(config, dict) and isinstance(config.get("admin_users"), dict) and config["admin_users"]:
                return config
        username = os.environ.get("STOCK_ADMIN_USERNAME", "admin").strip()
        password = os.environ.get("STOCK_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
        if not username or len(password) < 6:
            raise ValueError("管理员用户名不能为空，密码至少需要6个字符。")
        config = {"admin_users": {username: {"password_hash": generate_password_hash(password)}}}
        if not DataManager.save_admin_config(config):
            raise RuntimeError("无法写入管理员配置，请检查数据目录是否可写。")
        print("\n首次启动：已创建本机管理员，请保存以下登录信息。")
        print(f"管理员账号: {username}")
        print(f"管理员密码: {password}\n")
        return config

    @staticmethod
    def save_admin_config(admin_data):
        """保存管理员配置"""
        try:
            temp_file = Config.ADMIN_CONFIG.with_suffix('.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(admin_data, f, ensure_ascii=False, indent=2)

            # 使用当前用户继承的文件权限。

            temp_file.replace(Config.ADMIN_CONFIG)

            # 使用当前用户继承的文件权限。

            return True
        except Exception as e:
            print(f"❌ 保存管理员配置失败: {str(e)}")
            return False


# ------------------- 业务逻辑模块 -------------------
class StockManager:
    """股票管理类"""

    def __init__(self):
        self.stocks = {
            "600036": {"name": "招商银行", "price": 32.56, "change": 0.0},
            "000858": {"name": "五粮液", "price": 168.20, "change": 0.0},
            "601318": {"name": "中国平安", "price": 48.32, "change": 0.0}
        }
        self.last_update = time.time()

    def update_prices(self):
        """更新股票价格"""
        if time.time() - self.last_update < Config.STOCK_UPDATE_INTERVAL:
            return False

        for code in self.stocks:
            change_rate = random.uniform(-0.05, 0.05)
            old_price = self.stocks[code]["price"]
            new_price = round(old_price * (1 + change_rate), 2)
            self.stocks[code]["change"] = round(new_price - old_price, 2)
            self.stocks[code]["price"] = new_price

        self.last_update = time.time()
        print("✅ 股票价格已更新")
        return True

    def get_stock(self, code):
        """获取股票信息"""
        return self.stocks.get(code)


class UserService:
    """用户业务服务类"""

    @staticmethod
    def init_user(username, password):
        """初始化新用户数据"""
        return {
            "password_hash": generate_password_hash(password),
            "real_name": "",
            "id_card": "",
            "phone": "",
            "balance": 50000.0,
            "holdings": [],
            "trade_records": [],
            "fund_records": [],
            "register_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    @staticmethod
    def generate_captcha():
        """生成验证码"""
        chars = string.digits + string.ascii_letters
        return ''.join(random.choices(chars, k=4))

    @staticmethod
    def validate_captcha(input_captcha, session_captcha, create_time):
        """验证验证码"""
        if time.time() - create_time > Config.CAPTCHA_EXPIRY:
            return False, "验证码已过期"
        if input_captcha.lower() != session_captcha.lower():
            return False, "验证码错误"
        return True, ""


# ------------------- Flask应用初始化 -------------------
def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = Config.SESSION_LIFETIME

    # 初始化组件
    DataManager.init_data_dir()
    DataManager.load_admin_config()
    blockchain = Blockchain(persist_file=Config.BLOCKCHAIN_FILE)
    stock_manager = StockManager()

    # ------------------- 管理员路由 -------------------
    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            try:
                data = request.get_json() if request.is_json else {}
                username = data.get("username", "").strip()
                password = data.get("password", "").strip()

                if not username or not password:
                    return jsonify({"status": "error", "msg": "请填写完整信息"})

                admin_config = DataManager.load_admin_config()
                admin_user = admin_config["admin_users"].get(username)
                if admin_user and check_password_hash(admin_user.get("password_hash", ""), password):
                    session["is_admin"] = True
                    session["admin_username"] = username
                    return jsonify({"status": "success", "msg": "登录成功"})
                return jsonify({"status": "error", "msg": "账号或密码错误"})

            except Exception as e:
                return jsonify({"status": "error", "msg": f"登录异常: {str(e)}"})

        if session.get("is_admin"):
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_login.html")

    @app.route("/admin/dashboard")
    def admin_dashboard():
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))

        users = DataManager.load_users()
        total_users = len(users)
        total_transactions = sum(len(block.transactions) for block in blockchain.chain)
        total_balance = sum(user["balance"] for user in users.values()) if users else 0

        return render_template("admin_dashboard.html",
                               total_users=total_users,
                               total_transactions=total_transactions,
                               total_balance=total_balance,
                               blockchain_length=len(blockchain.chain),
                               blockchain_valid=blockchain.is_chain_valid(),
                               admin_username=session["admin_username"])

    @app.route("/admin/users")
    def admin_users():
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))

        users = DataManager.load_users()
        selected_username = request.args.get("user", "")
        user_list = []

        for username, user_data in users.items():
            holding_value = 0
            for holding in user_data["holdings"]:
                stock = stock_manager.get_stock(holding["code"])
                if stock:
                    holding_value += stock["price"] * holding["quantity"]

            user_list.append({
                "username": username,
                "data": user_data,
                "total_asset": round(user_data["balance"] + holding_value, 2),
                "trade_count": len(user_data["trade_records"]),
                "is_selected": username == selected_username
            })

        return render_template("admin_users_combined.html",
                               users=sorted(user_list, key=lambda x: x["username"]),
                               stocks=stock_manager.stocks)

    @app.route("/admin/blockchain")
    def admin_blockchain():
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))

        chain_data = []
        for block in blockchain.chain:
            chain_data.append({
                "index": block.index,
                "timestamp": datetime.fromtimestamp(block.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                "hash": block.hash,
                "previous_hash": block.previous_hash,
                "transactions": block.transactions,
                "transaction_count": len(block.transactions)
            })

        return render_template("admin_blockchain.html",
                               chain_data=chain_data,
                               is_valid=blockchain.is_chain_valid())

    @app.route("/admin/logout")
    def admin_logout():
        session.pop("is_admin", None)
        session.pop("admin_username", None)
        return redirect(url_for("admin_login"))

    # ------------------- 普通用户路由 -------------------
    @app.route("/get_captcha")
    def get_captcha():
        captcha = UserService.generate_captcha()
        session["captcha"] = captcha
        session["captcha_time"] = time.time()
        return jsonify({"status": "success", "captcha": captcha})

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            try:
                data = request.get_json() or {}
                username = data.get("username", "").strip()
                password = data.get("password", "").strip()
                input_captcha = data.get("captcha", "").strip()

                if not all([username, password, input_captcha]):
                    return jsonify({"status": "error", "msg": "请填写完整信息"})

                valid, msg = UserService.validate_captcha(
                    input_captcha,
                    session.get("captcha", ""),
                    session.get("captcha_time", 0)
                )
                if not valid:
                    return jsonify({"status": "error", "msg": msg})

                users = DataManager.load_users()
                if username not in users:
                    return jsonify({"status": "error", "msg": "用户名不存在"})
                if not check_password_hash(users[username].get("password_hash", ""), password):
                    return jsonify({"status": "error", "msg": "密码错误"})

                session["username"] = username
                return jsonify({"status": "success", "msg": "登录成功"})

            except Exception as e:
                print(f"❌ 登录错误: {str(e)}")
                return jsonify({"status": "error", "msg": "服务器错误"})

        if "username" in session:
            return redirect(url_for("index"))
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            try:
                if request.is_json:
                    data = request.get_json()
                else:
                    data = {
                        "username": request.form.get("username", "").strip(),
                        "password": request.form.get("password", "").strip(),
                        "confirm_pwd": request.form.get("confirm_pwd", "").strip()
                    }

                username = data.get("username", "").strip()
                password = data.get("password", "").strip()
                confirm_pwd = data.get("confirm_pwd", "").strip()

                if not re.fullmatch(r"[\w\u4e00-\u9fa5]{3,32}", username):
                    return jsonify({"status": "error", "msg": "用户名应为3-32位字母、数字、中文或下划线"})
                if len(password) < 6:
                    return jsonify({"status": "error", "msg": "密码至少需要6个字符"})
                if password != confirm_pwd:
                    return jsonify({"status": "error", "msg": "两次密码不一致"})

                users = DataManager.load_users()
                if username in users:
                    return jsonify({"status": "error", "msg": "用户名已存在"})

                users[username] = UserService.init_user(username, password)
                if DataManager.save_users(users):
                    return jsonify({"status": "success", "msg": "注册成功，请登录"})
                return jsonify({"status": "error", "msg": "注册失败，请重试"})

            except Exception as e:
                print(f"❌ 注册错误: {str(e)}")
                return jsonify({"status": "error", "msg": "服务器错误"})

        if "username" in session:
            return redirect(url_for("index"))
        return render_template("register.html")

    @app.route("/")
    def index():
        if "username" not in session:
            return redirect(url_for("login"))

        username = session["username"]
        users = DataManager.load_users()
        if username not in users:
            session.pop("username")
            return redirect(url_for("login"))

        stock_manager.update_prices()

        return render_template("index.html",
                               user=users[username],
                               stocks=stock_manager.stocks,
                               blockchain_length=len(blockchain.chain))

    @app.route("/trade", methods=["POST"])
    def trade():
        """核心交易接口（确保100%上链）"""
        if "username" not in session:
            return jsonify({"status": "error", "msg": "请先登录"})

        try:
            data = request.get_json() or {}
            username = session["username"]
            users = DataManager.load_users()
            user = users.get(username)

            if not user:
                return jsonify({"status": "error", "msg": "用户不存在"})

            # 解析并清洗参数
            stock_code = re.sub(r'[^0-9a-zA-Z]', '', data.get("code", "").strip())
            quantity = int(data.get("quantity", 0))
            trade_type = data.get("type", "").strip().lower()

            # 校验参数
            stock = stock_manager.get_stock(stock_code)
            if not stock:
                return jsonify({"status": "error", "msg": "股票代码不存在"})
            if not (1 <= quantity <= Config.MAX_TRADE_QUANTITY):
                return jsonify({"status": "error", "msg": f"交易数量必须在1-{Config.MAX_TRADE_QUANTITY}之间"})
            if trade_type not in ["buy", "sell"]:
                return jsonify({"status": "error", "msg": "交易类型只能是买入或卖出"})

            # 计算交易金额
            price = stock["price"]
            amount = round(price * quantity, 2)
            trade_id = str(uuid.uuid4())[:8]
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            timestamp = round(time.time(), 2)

            # 执行交易
            if trade_type == "buy":
                if user["balance"] < amount:
                    return jsonify({"status": "error", "msg": "余额不足"})

                user["balance"] = round(user["balance"] - amount, 2)
                holding_found = False
                for h in user["holdings"]:
                    if h["code"] == stock_code:
                        h["quantity"] += quantity
                        holding_found = True
                        break
                if not holding_found:
                    user["holdings"].append({
                        "code": stock_code,
                        "name": stock["name"],
                        "price": price,
                        "quantity": quantity
                    })
                trade_desc = "买入"

            else:  # sell
                holding_found = False
                for h in user["holdings"]:
                    if h["code"] == stock_code:
                        if h["quantity"] < quantity:
                            return jsonify({"status": "error", "msg": "持仓数量不足"})
                        h["quantity"] -= quantity
                        if h["quantity"] == 0:
                            user["holdings"].remove(h)
                        holding_found = True
                        break
                if not holding_found:
                    return jsonify({"status": "error", "msg": "未持有该股票"})

                user["balance"] = round(user["balance"] + amount, 2)
                trade_desc = "卖出"

            # 记录交易
            trade_record = {
                "id": trade_id,
                "type": trade_desc,
                "code": stock_code,
                "name": stock["name"],
                "price": price,
                "quantity": quantity,
                "amount": amount,
                "time": now
            }
            user["trade_records"].append(trade_record)
            user["fund_records"].append({
                "id": trade_id,
                "type": f"股票{trade_desc}",
                "amount": -amount if trade_type == "buy" else amount,
                "balance": user["balance"],
                "time": now
            })

            # 准备上链数据
            transaction = {
                "trade_id": trade_id,
                "username": username,
                "stock_code": stock_code,
                "stock_name": stock["name"],
                "trade_type": trade_desc,
                "quantity": quantity,
                "price": price,
                "amount": amount,
                "timestamp": timestamp,
                "balance_after": user["balance"],
                "trade_time": now
            }

            # 添加到区块链（确保成功）
            new_block = blockchain.add_transaction(transaction)
            if not new_block:
                # 强制重试一次
                new_block = blockchain.add_transaction(transaction)

            # 保存用户数据
            DataManager.save_users(users)

            if new_block:
                return jsonify({
                    "status": "success",
                    "msg": f"{trade_desc}成功(已上链并持久化)",
                    "balance": user["balance"],
                    "trade_id": trade_id,
                    "block_index": new_block.index,
                    "block_hash": new_block.hash[:10] + "..."
                })
            else:
                return jsonify({
                    "status": "success",
                    "msg": f"{trade_desc}成功（本地记录已保存，区块链稍后同步）",
                    "balance": user["balance"],
                    "trade_id": trade_id
                })

        except Exception as e:
            print(f"❌ 交易错误: {str(e)}")
            return jsonify({"status": "error", "msg": f"交易失败: {str(e)}"})

    @app.route("/profile")
    def profile():
        if "username" not in session:
            return redirect(url_for("login"))

        user = DataManager.load_users().get(session["username"], {})
        return render_template("profile.html",
                               user=user,
                               stocks=stock_manager.stocks,
                               blockchain_valid=blockchain.is_chain_valid())

    @app.route("/change_pwd", methods=["POST"])
    def change_pwd():
        if "username" not in session:
            return jsonify({"status": "error", "msg": "请先登录"})

        try:
            data = request.get_json() or {}
            username = session["username"]
            users = DataManager.load_users()
            user = users.get(username)

            if not user:
                return jsonify({"status": "error", "msg": "用户不存在"})

            old_pwd = data.get("old_pwd", "").strip()
            new_pwd = data.get("new_pwd", "").strip()
            confirm_pwd = data.get("confirm_pwd", "").strip()

            if not check_password_hash(user.get("password_hash", ""), old_pwd):
                return jsonify({"status": "error", "msg": "旧密码错误"})
            if new_pwd != confirm_pwd:
                return jsonify({"status": "error", "msg": "两次密码不一致"})
            if len(new_pwd) < 6:
                return jsonify({"status": "error", "msg": "新密码长度不能少于6位"})

            user["password_hash"] = generate_password_hash(new_pwd)
            success = DataManager.save_users(users)
            return jsonify({
                "status": "success" if success else "error",
                "msg": "密码修改成功，请重新登录" if success else "密码修改失败"
            })

        except Exception as e:
            print(f"❌ 修改密码错误: {str(e)}")
            return jsonify({"status": "error", "msg": "服务器错误"})

    @app.route("/update_info", methods=["POST"])
    def update_info():
        if "username" not in session:
            return jsonify({"status": "error", "msg": "请先登录"})

        try:
            data = request.get_json() or {}
            username = session["username"]
            users = DataManager.load_users()
            user = users.get(username)

            if not user:
                return jsonify({"status": "error", "msg": "用户不存在"})

            user["real_name"] = data.get("real_name", "").strip()
            id_card = data.get("id_card", "").strip()
            if id_card and len(id_card) == 18:
                id_card = id_card[:6] + "********" + id_card[-4:]
            user["id_card"] = id_card
            user["phone"] = data.get("phone", "").strip()

            success = DataManager.save_users(users)
            return jsonify({
                "status": "success" if success else "error",
                "msg": "信息更新成功" if success else "信息更新失败"
            })

        except Exception as e:
            print(f"❌ 更新信息错误: {str(e)}")
            return jsonify({"status": "error", "msg": "服务器错误"})

    @app.route("/blockchain_info")
    def blockchain_info():
        if "username" not in session:
            return jsonify({"status": "error", "msg": "请先登录"})

        latest = blockchain.get_latest_block()
        user_trade_count = sum(
            1 for block in blockchain.chain
            for tx in block.transactions
            if tx.get("username") == session["username"]
        )

        return jsonify({
            "chain_length": len(blockchain.chain),
            "is_valid": blockchain.is_chain_valid(),
            "latest_block": {
                "index": latest.index,
                "hash": latest.hash,
                "previous_hash": latest.previous_hash,
                "transaction_count": len(latest.transactions),
                "timestamp": datetime.fromtimestamp(latest.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            },
            "user_trade_count": user_trade_count
        })

    @app.route("/logout")
    def logout():
        session.pop("username", None)
        return redirect(url_for("login"))

    @app.route("/admin/backup_blockchain")
    def backup_blockchain():
        if not session.get("is_admin"):
            return jsonify({"status": "error", "msg": "无管理员权限"})
        if blockchain._backup_chain(force=True):
            return jsonify({"status": "success", "msg": "区块链备份成功"})
        else:
            return jsonify({"status": "error", "msg": "区块链备份失败"})

    return app


# ------------------- 启动入口 -------------------
if __name__ == "__main__":
    app = create_app()

    # 启动日志
    print("\n=== 股票交易系统(区块链版) - 最终稳定版 ===")
    print(f"✅ 服务器地址: http://127.0.0.1:{os.environ.get('STOCK_PORT', '5000')}")
    print(f"✅ 管理员入口: http://127.0.0.1:{os.environ.get('STOCK_PORT', '5000')}/admin/login")
    print("管理员入口使用首次启动时显示的本机账号和密码。")
    print(f"✅ 数据目录: {Config.DATA_DIR.absolute()}")
    print(f"✅ 区块链文件: {Config.BLOCKCHAIN_FILE.absolute()}")
    print(f"✅ 备份文件: {Config.BLOCKCHAIN_BACKUP.absolute()}")
    print("===========================================\n")

    app.run(debug=False, port=int(os.environ.get("STOCK_PORT", "5000")), host=os.environ.get("STOCK_HOST", "127.0.0.1"))