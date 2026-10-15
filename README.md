# 基于区块链的股票交易系统

可下载到本机运行的 Flask 股票交易教学项目。包含用户注册、图形页面验证码、登录、模拟股票买卖、持仓和资金记录、个人资料、管理员后台，以及交易区块的哈希校验与本地备份。

本项目使用模拟行情和虚拟资金，交易保存到本机 JSON 哈希链；不需要数据库、区块链节点或行情 API。首次安装依赖后，页面样式和交互资源均从本机加载。

## 下载

- [下载本分支完整 ZIP](https://github.com/thv-television-hongkong/thv-day01/archive/refs/heads/blockchain-stock-trading.zip)，然后先解压到一个可写的文件夹。
- 或通过 Git 下载独立分支：

```bash
git clone --single-branch --branch blockchain-stock-trading https://github.com/thv-television-hongkong/thv-day01.git
cd thv-day01
```

## Windows 快速启动

1. 安装 [Python 3.10 或更高版本](https://www.python.org/downloads/)，安装时勾选 **Add Python to PATH**。
2. 解压项目后，双击 `start.bat`。脚本会建立独立虚拟环境并安装依赖；首次安装需要联网。
3. 保持终端窗口打开，在浏览器访问 **http://127.0.0.1:5000**。
4. 点击“立即注册”，创建自己的用户。新用户获得 50,000 元模拟资金，可以在交易页面买入、卖出股票。

停止运行时，在终端按 `Ctrl+C`。再次双击 `start.bat` 会继续使用本机原有数据。

## macOS / Linux

```bash
sh start.sh
```

如系统没有 `venv` 模块，先安装对应的 Python venv 软件包，再重新运行。也可以手动启动：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Windows 手动启动时，将上述 Python 路径换成 `.venv\Scripts\python.exe`。

## 管理员后台

后台地址：**http://127.0.0.1:5000/admin/login**。

第一次运行时，程序会自动创建用户名为 `admin` 的管理员，并在启动终端显示随机密码。请保存该密码；项目没有预置通用管理员口令。

可在首次运行前通过环境变量指定管理员，例如在 Windows 命令提示符中：

```bat
set STOCK_ADMIN_USERNAME=admin
set STOCK_ADMIN_PASSWORD=请替换成你自己的密码
start.bat
```

这两个变量只在管理员配置尚未生成时生效。忘记密码时，先停止程序，仅删除本机 `data/admin.json`，再启动即可重新生成管理员；用户和交易记录不受影响。

## 文件与数据

```text
app.py             程序入口及业务逻辑
templates/         8 个用户端和管理端网页
static/            本地 Bootstrap 样式、脚本和许可证
requirements.txt   Python 依赖
start.bat          Windows 启动脚本
start.sh           macOS / Linux 启动脚本
test_app.py        可重复运行的完整流程验证
data/              首次运行自动生成的本机数据
```

本机数据包括 `users.json`、`admin.json`、`blockchain.json` 和 `blockchain_backup.json`；密码以哈希形式保存。发行包不包含开发电脑上的账户、个人资料或历史交易，`data/` 也已加入 Git 忽略规则。

股票价格是内置初始价格加模拟波动，用户交易生成新的区块，并提供前后区块哈希校验。它适合本机学习和演示，采用单进程和本地文件存储。

## 常见问题

- **端口 5000 被占用**：先关闭此前启动的实例，或设置 `STOCK_PORT=5001` 后运行 `app.py`，然后打开 `http://127.0.0.1:5001`。
- **依赖安装失败**：检查网络，确认 Python 版本符合要求，重试启动脚本；Windows 也可执行 `.venv\Scripts\python.exe -m pip install -r requirements.txt`。
- **页面打不开**：保持启动终端运行，查看是否出现 `Running on http://127.0.0.1:5000`，并使用 HTTP 地址。
- **需要备份**：停止程序后复制整个 `data/` 文件夹。恢复时放回相同位置。
- **需要全新演示数据**：停止程序后先备份，再删除本机 `data/` 文件夹，下次启动会重新初始化。

默认只监听 `127.0.0.1`。可通过 `STOCK_HOST`、`STOCK_PORT` 和 `STOCK_DATA_DIR` 分别指定监听地址、端口和本机数据位置。

## 验证

安装依赖后运行：

```bash
python -m unittest test_app -v
```

测试使用临时目录，覆盖首次初始化、注册和验证码登录、买卖交易、资金与持仓、区块链校验、数据重载、密码修改及管理员页面，不读取或修改你的日常数据。

## 来源

从作者本机的“22 基于区块链的股票交易系统”完整项目整理，补齐网页模板、静态资源、依赖和启动脚本，并修复首次管理员初始化与注册跳转。

Bootstrap 5.3.0 采用 MIT 许可证，许可证全文见 `static/BOOTSTRAP_LICENSE.txt`。
