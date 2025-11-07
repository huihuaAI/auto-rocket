# RocketGo 自动回复机器人

## 项目结构

```
PythonProject/
├── main.py              # 🚀 主入口文件
├── config.py            # ⚙️ 配置管理
├── client.py            # 🌐 RocketGo客户端
├── playwright_ws.py     # 🎭 Playwright WebSocket客户端
├── reply_handler.py     # 📤 消息发送处理
├── chat_processor.py    # 🤖 消息处理逻辑
├── dify_client.py       # 🧠 Dify AI客户端
├── db_manager.py        # 💾 数据库管理
├── 验证码识别.py        # 🔍 验证码识别工具
└── conversations.db     # 📊 SQLite数据库（自动创建）
```

## 文件说明

### 核心文件

- **main.py** - 程序主入口，负责启动和协调各个模块
- **config.py** - 集中管理所有配置项，支持环境变量
- **client.py** - RocketGo平台客户端，处理登录和协调WebSocket连接
- **playwright_ws.py** - 基于Playwright的WebSocket客户端，绕过Cloudflare保护

### 功能模块

- **reply_handler.py** - 集成消息处理器，负责消息发送和完整流程管理
- **chat_processor.py** - 消息处理逻辑，解析WebSocket消息并调用AI
- **dify_client.py** - Dify AI API客户端，支持持久化对话
- **db_manager.py** - SQLite数据库管理，存储conversation_id

### 工具模块

- **验证码识别.py** - 验证码识别功能，用于自动登录

## 使用方法

### 1. 基本使用
```bash
python main.py
```

### 2. 环境变量配置（推荐）
```bash
export ROCKETGO_USER="your_username"
export ROCKETGO_PASS="your_password"
export DIFY_API_KEY="your_dify_api_key"
python main.py
```

### 3. 配置文件修改
直接编辑 `config.py` 中的默认值。

## 功能特性

✅ **自动登录** - 支持验证码识别，自动处理登录流程
✅ **智能对话** - 集成Dify AI，支持上下文记忆
✅ **持久化** - 使用SQLite存储对话状态，重启后继续对话
✅ **自动回复** - 监听用户消息，自动生成并发送回复
✅ **Cloudflare绕过** - 使用Playwright绕过Cloudflare保护
✅ **断线重连** - 自动处理网络断线重连
✅ **多用户支持** - 每个用户独立的对话记录
✅ **配置灵活** - 支持环境变量和配置文件两种方式

## 运行流程

1. **启动** → 读取配置，设置日志
2. **登录** → 自动处理验证码，获取认证token
3. **初始化** → 获取会话信息，初始化AI处理器
4. **WebSocket连接** → 使用Playwright绕过Cloudflare建立连接
5. **监听** → 持续监听用户消息
6. **处理** → 解析消息 → 调用AI → 发送回复
7. **持久化** → 保存对话状态到数据库

## 注意事项

- 首次运行会自动创建 `conversations.db` 数据库文件
- 验证码图片会临时保存为 `验证码.png`
- 日志会同时输出到控制台和 `auto_reply.log` 文件
- 按 `Ctrl+C` 可安全退出程序