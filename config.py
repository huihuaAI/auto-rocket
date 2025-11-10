import tomllib
from pathlib import Path
import keyring

CONFIG_PATH = Path(__file__).parent / "config.toml"
SERVICE_NAME = "auto_rocket"


class AttrDict(dict):
    def __getattr__(self, item):
        value = self.get(item)
        if isinstance(value, dict):
            return AttrDict(value)
        return value

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def load_config():
    with open(CONFIG_PATH, "rb") as f:
        cfg = tomllib.load(f)
        return AttrDict(cfg)


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
