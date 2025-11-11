import tomllib
import sys
from pathlib import Path
import keyring
import os
import shutil

def get_user_data_dir():
    """获取用户数据目录（跨平台）"""
    app_name = "RocketGo"

    if sys.platform == 'darwin':
        data_dir = Path.home() / 'Library' / 'Application Support' / app_name
    elif sys.platform == 'win32':
        data_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / app_name
    else:
        data_dir = Path.home() / '.local' / 'share' / app_name

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_bundled_resource_path(relative_path):
    """获取打包资源的路径（兼容PyInstaller）"""
    try:
        # PyInstaller 创建的临时文件夹路径
        if hasattr(sys, '_MEIPASS'):
            # 在 macOS .app 包中，资源在 Contents/Resources/
            if sys.platform == 'darwin':
                base_path = Path(sys._MEIPASS).parent / 'Resources'
            else:
                base_path = Path(sys._MEIPASS)
        else:
            # 开发环境，使用脚本所在目录
            base_path = Path(__file__).parent
    except Exception:
        base_path = Path(__file__).parent

    return base_path / relative_path


def setup_config_file():
    """确保用户数据目录有 config.toml 文件"""
    user_data_dir = get_user_data_dir()
    user_config_file = user_data_dir / 'config.toml'

    # 如果用户数据目录没有 config.toml 文件
    if not user_config_file.exists():
        # 尝试从打包资源复制
        bundled_config = get_bundled_resource_path('config.toml')
        if bundled_config.exists():
            shutil.copy2(bundled_config, user_config_file)
            print(f"已从打包资源复制 config.toml 到: {user_config_file}")
        else:
            # 如果打包资源也没有，尝试从开发环境复制
            dev_config = Path(__file__).parent / 'config.toml'
            if dev_config.exists():
                shutil.copy2(dev_config, user_config_file)
                print(f"已从开发环境复制 config.toml 到: {user_config_file}")
            else:
                print(f"警告: 找不到 config.toml 文件")

    return user_config_file


# 获取用户数据目录
USER_DATA_DIR = get_user_data_dir()

# 获取配置文件路径
def get_config_path():
    """获取配置文件路径，兼容开发和打包环境"""
    if getattr(sys, 'frozen', False):
        # 打包环境：使用用户数据目录，并确保文件存在
        return setup_config_file()
    else:
        # 开发环境：使用当前目录
        return Path(__file__).parent / 'config.toml'


CONFIG_PATH = get_config_path()
SERVICE_NAME = "auto_rocket"


def get_data_file_path(filename):
    """
    获取数据文件路径（日志、数据库、验证码图片等）
    所有数据文件都存放在用户数据目录

    Args:
        filename: 文件名或相对路径

    Returns:
        Path: 文件的完整路径
    """
    if not filename:
        return USER_DATA_DIR

    # 如果已经是绝对路径，直接返回
    file_path = Path(filename)
    if file_path.is_absolute():
        return file_path

    # 相对路径：放在用户数据目录
    return USER_DATA_DIR / filename


class AttrDict(dict):
    def __getattr__(self, item):
        value = self.get(item)
        if isinstance(value, dict):
            return AttrDict(value)
        return value

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def load_config():
    """加载配置文件，添加异常处理"""
    try:
        config_path = get_config_path()
        if not config_path or not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "rb") as f:
            cfg = tomllib.load(f)
            return AttrDict(cfg)
    except FileNotFoundError as e:
        import logging
        logging.error(f"配置文件加载失败: {e}")
        # 返回一个空的默认配置，避免程序崩溃
        return AttrDict({
            'log': {'level': 'INFO', 'file': 'auto_reply.log'},
            'rocketgo': {},
            'dify': {},
            'send': {},
            'db': {'path': 'conversations.db'},
            'other': {}
        })
    except Exception as e:
        import logging
        logging.error(f"配置文件解析失败: {e}")
        raise


def set_credentials(username: str, password: str):
    keyring.set_password(SERVICE_NAME, username, password)


def get_credentials(username: str):
    password = keyring.get_password(SERVICE_NAME, username)
    return username, password


def save_last_username(username: str):
    """保存最后使用的用户名"""
    keyring.set_password(SERVICE_NAME, "__last_username__", username)


def get_last_username():
    """获取最后使用的用户名"""
    return keyring.get_password(SERVICE_NAME, "__last_username__")


config = load_config()


if __name__ == "__main__":
    print(config.dify.input)
