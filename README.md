# Auto Rocket GUI

这是一个针对火箭（RocketGo）平台的自动控制GUI应用程序。

## 项目结构

```
auto-rocket-gui/
├── main.py                 # 主入口文件
├── config.py              # 配置加载模块
├── config.toml            # 配置文件
├── core/                  # 核心业务逻辑层
│   ├── __init__.py
│   ├── auth_manager.py    # 认证管理
│   ├── http_client.py     # HTTP客户端
│   ├── client.py          # RocketGo客户端
│   ├── ws.py              # WebSocket客户端
│   ├── chat_processor.py  # 消息处理器
│   ├── conversation_monitor.py  # 对话监听服务
│   ├── dify.py            # Dify AI集成
│   ├── db_manage.py       # 数据库管理
│   ├── message_splitter.py # 消息分段器
│   └── message_service.py  # 消息服务接口
├── services/              # 服务层（降低耦合）
│   ├── __init__.py
│   ├── rocket_service.py  # RocketGo服务（整合所有功能）
│   └── scheduler_service.py # 定时重启服务
└── gui/                   # GUI界面层
    ├── __init__.py
    ├── login_window.py    # 登录窗口
    └── main_window.py     # 主窗口
```

## 功能特性

### 1. 登录功能
- 用户名密码登录
- 自动验证码识别
- 记住密码功能（使用系统keyring）
- 登录失败自动重试（最多3次）

### 2. 主界面功能

#### 控制面板
- **服务控制**: 启动/停止/重启 WebSocket连接
- **定时重启**: 可配置的自动重启功能（防止token过期）
  - 可设置最小和最大重启间隔
  - 随机间隔防止检测
  - 显示下次重启时间
- **对话监听服务**: 自动跟进长时间未回复的对话
  - 可配置检查间隔
  - 可配置超时阈值
  - 可配置最大激活次数

#### 配置编辑
- 直接在GUI中编辑 `config.toml` 文件
- 保存后提示重启服务生效
- 支持所有配置项的修改

#### 日志查看
- 实时显示运行日志
- 按级别着色（INFO/WARNING/ERROR）
- 支持清空日志
- 自动滚动到最新消息

### 3. 核心功能

#### WebSocket消息处理
- 自动连接和重连
- 心跳保活（每5秒）
- 消息自动处理和回复
- 支持多种消息类型（文本/图片/视频/音频）

#### Dify AI集成
- 智能对话回复
- 支持上下文管理
- 对话历史持久化
- 支持文件和图片输入

#### 对话监听
- 定期检查数据库中的对话
- 自动跟进超时未回复的对话
- 防止过度激活（可配置最大次数）

## 使用方法

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

需要安装的主要依赖：
- tkinter（Python自带）
- aiohttp
- websockets
- sqlalchemy
- ddddocr（验证码识别）
- Pillow（图片处理）
- keyring（密码存储）

### 2. 配置文件

编辑 `config.toml` 文件，配置以下内容：

```toml
# RocketGo 平台配置
[rocketgo]
login_url = "https://pn3cs.rocketgo.vip/prod-api2/login"
# ... 其他URL配置

# Dify AI 配置
[dify]
url = "你的Dify API地址"
api_key = "你的Dify API密钥"

[dify.input]
register_url = ""
whatsapp_url = ""
hr_name = ""
language = ""
is_return_visit = 0

# 数据库配置
[db]
path = "conversations.db"
```

### 3. 运行程序

```bash
python3 main.py
```

### 4. 使用流程

1. **登录**
   - 启动程序后会显示登录窗口
   - 输入用户名和密码
   - 勾选"记住密码"可保存凭据
   - 点击"登录"按钮

2. **主界面操作**
   - 登录成功后进入主界面
   - 点击"启动服务"开始WebSocket连接
   - 在右侧日志窗口查看运行状态
   - 根据需要启用定时重启和对话监听

3. **配置修改**
   - 切换到"配置编辑"标签页
   - 直接修改配置内容
   - 点击"保存配置"
   - 重启服务使配置生效

## 架构设计

### 分层架构

1. **GUI层** (`gui/`)
   - 只负责界面展示和用户交互
   - 通过回调与服务层通信
   - 不包含业务逻辑

2. **服务层** (`services/`)
   - 整合核心功能，提供统一接口
   - 管理服务生命周期
   - 降低GUI和核心层的耦合

3. **核心层** (`core/`)
   - 独立的业务逻辑模块
   - 可以单独使用，不依赖GUI
   - 每个模块职责单一

### 设计模式

- **依赖注入**: 服务层通过构造函数注入依赖
- **观察者模式**: 使用回调函数通知状态变化
- **单一职责**: 每个模块只负责一个功能
- **接口隔离**: 使用Protocol定义接口

## 注意事项

1. **Token过期**: WebSocket和Token会在3小时左右过期，建议启用定时重启功能

2. **验证码识别**: 使用ddddocr进行验证码识别，准确率约90%，失败会自动重试

3. **消息分段**: 如果Dify返回的消息包含`&&&`分隔符，会自动分段发送

4. **数据库**: 使用SQLite存储对话历史，文件位置在`conversations.db`

5. **日志文件**: 默认保存在`auto_reply.log`，可在配置文件中修改

## 故障排除

### 登录失败
- 检查网络连接
- 确认用户名密码正确
- 查看日志中的详细错误信息

### WebSocket连接失败
- 确保已成功登录
- 检查token是否有效
- 查看防火墙设置

### 消息处理失败
- 检查Dify配置是否正确
- 确认API密钥有效
- 查看日志中的错误详情

## 开发说明

### 添加新功能

1. 在 `core/` 中实现核心逻辑
2. 在 `services/` 中整合到服务层
3. 在 `gui/` 中添加界面元素

### 修改配置

1. 编辑 `config.toml`
2. 在 `config.py` 中加载配置
3. 在需要的地方使用 `config.xxx`

### 日志记录

```python
import logging
logger = logging.getLogger(__name__)
logger.info("信息")
logger.warning("警告")
logger.error("错误")
```

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题，请查看日志文件或联系开发者。
