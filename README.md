# RocketGo 自动回复机器人

一个支持图形界面和命令行的智能客服机器人，基于 Dify AI 和 Playwright 构建。

## 项目结构

```
PythonProject/
├── launcher.py           # 🚀 统一启动器（支持GUI/CLI模式）
├── gui.py                # 🖥️ Tkinter图形界面
├── main.py               # 📟 CLI模式主入口
├── config.py             # ⚙️ 配置管理
├── client.py             # 🌐 RocketGo客户端
├── playwright_ws.py      # 🎭 Playwright WebSocket客户端
├── reply_handler.py      # 📤 消息发送处理
├── chat_processor.py     # 🤖 消息处理逻辑
├── dify_client.py        # 🧠 Dify AI客户端
├── db_manager.py         # 💾 数据库管理
├── logger_config.py      # 🎨 彩色日志配置
├── message_splitter.py   # ✂️ 消息分段服务
├── conversation_monitor.py # 👀 对话监听服务
├── 验证码识别.py         # 🔍 验证码识别工具
└── conversations.db      # 📊 SQLite数据库（自动创建）
```

## 文件说明

### 启动器

- **launcher.py** - 统一启动器，支持GUI模式（默认）和CLI模式

### 界面模块

- **gui.py** - 跨平台Tkinter图形界面，提供配置管理、运行控制、日志查看等功能
- **main.py** - CLI模式主入口，无图形界面运行

### 核心模块

- **config.py** - 集中管理所有配置项，支持环境变量
- **client.py** - RocketGo平台客户端，处理登录和协调WebSocket连接
- **playwright_ws.py** - 基于Playwright的WebSocket客户端，绕过Cloudflare保护

### 功能模块

- **reply_handler.py** - 消息发送处理器，负责消息发送流程管理
- **chat_processor.py** - 消息处理逻辑，解析WebSocket消息并调用AI
- **dify_client.py** - Dify AI API客户端，支持持久化对话和流式输出
- **db_manager.py** - SQLite数据库管理，存储conversation_id和对话状态
- **conversation_monitor.py** - 对话监听服务，定期检查并主动跟进超时对话
- **message_splitter.py** - 消息分段服务，支持使用分隔符分段发送长消息

### 工具模块

- **logger_config.py** - 彩色日志配置，提供美观的日志输出
- **验证码识别.py** - 验证码识别功能，用于自动登录

## 使用方法

### 1. GUI模式（推荐）

#### 启动GUI
```bash
python launcher.py
# 或明确指定GUI模式
python launcher.py --gui
```

GUI界面提供:
- 可视化配置管理（用户名、密码、API密钥等）
- 一键启动/停止控制
- 实时日志查看
- 日志导出功能
- 跨平台支持（Windows/macOS/Linux）

### 2. CLI模式（命令行）

#### 直接启动CLI
```bash
python launcher.py --cli
# 或使用别名
python launcher.py --headless
```

#### 传统方式（仅CLI）
```bash
python main.py
```

### 3. 配置文件（推荐）

#### 使用 .env 文件
```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的配置
vim .env  # 或使用其他编辑器

# 然后启动
python launcher.py
```

#### .env 文件示例
```bash
# RocketGo 登录凭据
ROCKETGO_USER=your_username
ROCKETGO_PASS=your_password

# Dify AI 配置
DIFY_URL=https://api.dify.ai/v1
DIFY_API_KEY=your_dify_api_key

# Dify 输入参数
INPUT_REGISTER_URL=https://example.com/register
INPUT_WHATSAPP_URL=https://wa.me/1234567890
INPUT_HR_NAME=Your HR Name
INPUT_LANGUAGE=中文
INPUT_IS_RETURN_VISIT=0

# 数据库配置
DB_PATH=conversations.db

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=auto_reply.log
```

### 4. GUI配置
也可以直接在GUI界面中进行可视化配置（启动后在配置管理面板中修改）。

> **注意**: 不要直接修改 `config.py`，请使用 `.env` 文件或GUI配置。

## 功能特性

### 核心功能
✅ **自动登录** - 支持验证码识别，自动处理登录流程
✅ **智能对话** - 集成Dify AI，支持上下文记忆和流式输出
✅ **持久化存储** - 使用SQLite存储对话状态，重启后继续对话
✅ **自动回复** - 监听用户消息，自动生成并发送回复
✅ **Cloudflare绕过** - 使用Playwright绕过Cloudflare保护
✅ **断线重连** - 自动处理网络断线重连
✅ **多用户支持** - 每个用户独立的对话记录

### 界面与交互
✅ **双模式支持** - GUI图形界面 + CLI命令行，适应不同使用场景
✅ **跨平台** - 支持Windows、macOS、Linux系统
✅ **彩色日志** - 美观易读的彩色日志输出，支持日志导出
✅ **可视化配置** - GUI界面中直观管理所有配置项

### 高级功能
✅ **消息分段** - 支持使用分隔符(&&&)将长消息分段发送
✅ **对话监听** - 定期检查超时对话，主动发送跟进消息
✅ **智能激活** - 防止过度打扰，控制主动消息频率
✅ **配置灵活** - 支持环境变量、配置文件、GUI配置三种方式

## 运行流程

### 启动流程
1. **选择模式** → GUI模式（默认）或 CLI模式
2. **读取配置** → 从环境变量/配置文件/GUI加载配置
3. **设置日志** → 初始化彩色日志系统

### 运行流程
4. **登录** → 自动处理验证码，获取认证token
5. **初始化** → 获取会话信息，初始化AI处理器
6. **WebSocket连接** → 使用Playwright绕过Cloudflare建立连接
7. **启动监听** → 启动消息监听和对话监听服务

### 消息处理
8. **接收消息** → 持续监听用户发送的消息
9. **AI处理** → 调用Dify AI生成智能回复
10. **分段发送** → 根据分隔符拆分并发送回复
11. **持久化** → 保存对话状态和conversation_id到数据库

### 主动跟进
12. **定期检查** → 每5秒检查超时对话（默认3小时）
13. **生成问候** → AI生成个性化跟进消息
14. **主动发送** → 向超时用户主动发送跟进消息
15. **控制频率** → 限制单个用户的主动激活次数（默认≤10次）

## 安装依赖

```bash
# 安装 Python 依赖
pip install playwright asyncio aiohttp python-dotenv

# 安装 Playwright 浏览器
playwright install chromium

# GUI 模式需要 tkinter (macOS 可能需要单独安装)
# macOS: brew install python-tk
# Ubuntu/Debian: sudo apt-get install python3-tk
```

## 快速开始

```bash
# 1. 复制配置文件
cp .env.example .env

# 2. 编辑配置文件，填入你的账号信息
vim .env

# 3. 启动程序（GUI模式）
python launcher.py

# 或启动 CLI 模式
python launcher.py --cli
```

## 注意事项

### 数据和文件
- 首次运行会自动创建 `conversations.db` 数据库文件
- 验证码图片会临时保存为 `验证码.png`
- 日志会同时输出到控制台和 `auto_reply.log` 文件
- `.env` 文件包含敏感信息，请勿提交到版本控制（已在 `.gitignore` 中）

### GUI模式
- GUI模式需要tkinter支持，macOS可能需要: `brew install python-tk`
- 如果GUI不可用，启动器会自动提示切换到CLI模式

### 运行控制
- GUI模式: 点击"停止"按钮或关闭窗口退出
- CLI模式: 按 `Ctrl+C` 安全退出程序

### 消息分段
- 在AI回复中使用 `&&&` 作为分隔符，系统会自动分段发送
- 示例: `第一段内容&&&第二段内容&&&第三段内容` → 依次发送3条消息

### 对话监听
- 默认每5秒检查一次超时对话
- 超时阈值: 3小时未互动
- 单个用户最多主动激活10次，避免过度打扰
- 可在 `conversation_monitor.py` 中调整这些参数

## 常见问题

### 1. GUI启动失败
```bash
# 检查tkinter是否安装
python -c "import tkinter"

# macOS安装
brew install python-tk

# Ubuntu/Debian安装
sudo apt-get install python3-tk
```

### 2. Playwright浏览器问题
```bash
# 重新安装Chromium
playwright install chromium
```

### 3. 配置优先级
.env 文件/环境变量 > GUI配置 > config.py 中的 os.getenv() 默认值

**推荐做法**：
- 开发/生产环境：使用 `.env` 文件
- 临时测试：使用环境变量 `export`
- 快速调整：使用 GUI 界面配置
- **不推荐**：直接修改 `config.py` 源码

## 技术栈

- **语言**: Python 3.8+
- **UI框架**: Tkinter (跨平台)
- **自动化**: Playwright (绕过Cloudflare)
- **AI对话**: Dify API
- **数据库**: SQLite
- **异步**: asyncio + aiohttp
- **日志**: logging (自定义彩色formatter)
- **配置管理**: python-dotenv (.env 文件)