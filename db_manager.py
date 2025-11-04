#!/usr/bin/env python3
"""
对话管理模块 - 使用SQLAlchemy存储conversation_id
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()

"""
account_id 是用户在 RocketGo 平台上的账号唯一标识符（对应 csUsername），用于关联好友的对话记录。
friend_id 是用户在 RocketGo 平台上的好友账号唯一标识符（对应 username），用于关联用户的好友对话记录。
conversation_id 是 Dify 平台上的对话唯一标识符，用于存储用户与好友的对话记录（首次为空，Dify返回后保存）。
created_at 是对话记录创建时间，用于记录对话开始的时间。
updated_at 是对话记录更新时间，用于记录最后一次更新对话记录的时间（每次接收消息时更新）。
active_count 是判断主动激活对话记录的次数，用于记录用户主动与好友开始对话的次数。
chat_user_id 是用户在 RocketGo 平台上的对话用户ID（对应 csChatUserId），用于关联用户与好友的对话记录。
"""


class Conversation(Base):
    """对话记录模型"""
    __tablename__ = 'conversations'

    chat_user_id = Column(String, primary_key=True, comment="用户在RocketGo平台上的对话用户ID（对应csChatUserId）")
    account_id = Column(String, nullable=False, comment='用户账号ID（csUsername）')
    friend_id = Column(String, nullable=False, comment='好友账号ID（username）')
    conversation_id = Column(String, nullable=True, comment='Dify对话ID')
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment='更新时间')
    active_count = Column(Integer, default=0, nullable=False, comment='主动激活次数')

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'chat_user_id': self.chat_user_id,
            'account_id': self.account_id,
            'friend_id': self.friend_id,
            'conversation_id': self.conversation_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'active_count': self.active_count
        }


class ConversationManager:
    """管理用户的conversation_id"""

    def __init__(self, db_path: str = "conversations.db"):
        self.db_path = db_path
        logger.info(f"初始化数据库管理器，路径: {db_path}")

        # 确保数据库文件的父目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                    logger.info(f"创建数据库目录: {db_dir}")
                except Exception as e:
                    logger.error(f"创建数据库目录失败: {e}")
                    raise
            else:
                logger.info(f"数据库目录已存在: {db_dir}")
                # 检查目录权限
                if not os.access(db_dir, os.W_OK):
                    logger.error(f"数据库目录不可写: {db_dir}")
                    raise PermissionError(f"数据库目录不可写: {db_dir}")

        # 处理路径中的空格和特殊字符
        db_path_obj = Path(db_path).resolve()
        logger.info(f"解析后的数据库路径: {db_path_obj}")

        # 使用简单的文件路径格式（四个斜杠表示绝对路径）
        # 这种方式在 Windows 和 Unix 系统上都能正确处理
        database_url = f'sqlite:///{db_path_obj}'
        logger.info(f"数据库 URL: {database_url}")

        try:
            # 添加 check_same_thread=False 以允许多线程访问
            self.engine = create_engine(
                database_url,
                echo=False,
                connect_args={'check_same_thread': False}
            )
            self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
            self._init_database()
        except Exception as e:
            logger.error(f"创建数据库引擎失败: {e}", exc_info=True)
            raise

    def _init_database(self):
        """初始化数据库表"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info(f"数据库初始化完成: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def _get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def get_conversation_id(self, chat_user_id: str) -> Optional[str]:
        """获取对话的conversation_id"""
        session = self._get_session()
        try:
            conversation = session.query(Conversation).filter_by(
                chat_user_id=chat_user_id,
            ).first()

            if conversation:
                logger.debug(f"找到对话记录: chat_user_id={chat_user_id}, conversation_id={conversation.conversation_id}")
                return conversation.conversation_id
            else:
                logger.debug(f"未找到对话记录: chat_user_id={chat_user_id}")
                return None
        except Exception as e:
            logger.error(f"获取conversation_id失败: {e}")
            return None
        finally:
            session.close()

    def save_conversation_id(self, chat_user_id: str, account_id: str, friend_id: str, conversation_id: str):
        """保存或更新conversation_id"""
        session = self._get_session()
        try:
            conversation = session.query(Conversation).filter_by(
                chat_user_id=chat_user_id
            ).first()

            if conversation:
                # 更新现有记录
                conversation.conversation_id = conversation_id
                conversation.account_id = account_id
                conversation.friend_id = friend_id
                conversation.updated_at = datetime.now()
                logger.info(f"更新对话记录: chat_user_id={chat_user_id}, account_id={account_id}, friend_id={friend_id}, conversation_id={conversation_id}")
            else:
                # 创建新记录
                conversation = Conversation(
                    chat_user_id=chat_user_id,
                    account_id=account_id,
                    friend_id=friend_id,
                    conversation_id=conversation_id
                )
                session.add(conversation)
                logger.info(f"创建新对话记录: chat_user_id={chat_user_id}, account_id={account_id}, friend_id={friend_id}, conversation_id={conversation_id}")

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"保存conversation_id失败: {e}")
            raise
        finally:
            session.close()

    def update_timestamp(self, chat_user_id: str):
        """更新对话的时间戳（每次接收消息时调用）"""
        session = self._get_session()
        try:
            conversation = session.query(Conversation).filter_by(
                chat_user_id=chat_user_id
            ).first()

            if conversation:
                conversation.updated_at = datetime.now()
                session.commit()
                logger.debug(f"更新对话时间戳: chat_user_id={chat_user_id}")
            else:
                # 如果不存在，创建一个新记录（conversation_id为空）
                conversation = Conversation(
                    chat_user_id=chat_user_id,
                    conversation_id=None
                )
                session.add(conversation)
                session.commit()
                logger.info(f"创建新对话记录（无conversation_id）: chat_user_id={chat_user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"更新时间戳失败: {e}")
            raise
        finally:
            session.close()

    def increment_active_count(self, chat_user_id: str, increment: int = 1):
        """增加主动激活次数"""
        session = self._get_session()
        try:
            conversation = session.query(Conversation).filter_by(
                chat_user_id=chat_user_id
            ).first()

            if conversation:
                conversation.active_count += increment
                conversation.updated_at = datetime.now()
                session.commit()
                logger.info(f"主动激活次数+{increment}: chat_user_id={chat_user_id}, count={conversation.active_count}")
            else:
                logger.warning(f"对话记录不存在，无法增加激活次数: chat_user_id={chat_user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"增加激活次数失败: {e}")
            raise
        finally:
            session.close()

    def get_conversation(self, chat_user_id: str) -> Optional[Dict]:
        """获取完整的对话记录"""
        session = self._get_session()
        try:
            conversation = session.query(Conversation).filter_by(
                chat_user_id=chat_user_id
            ).first()

            return conversation.to_dict() if conversation else None
        except Exception as e:
            logger.error(f"获取对话记录失败: {e}")
            return None
        finally:
            session.close()

    def delete_conversation(self, chat_user_id: str):
        """删除对话记录"""
        session = self._get_session()
        try:
            conversation = session.query(Conversation).filter_by(
                chat_user_id=chat_user_id
            ).first()

            if conversation:
                session.delete(conversation)
                session.commit()
                logger.info(f"删除对话记录: chat_user_id={chat_user_id}")
            else:
                logger.warning(f"对话记录不存在: chat_user_id={chat_user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"删除对话记录失败: {e}")
            raise
        finally:
            session.close()

    def list_all_conversations(self) -> List[Dict]:
        """列出所有对话记录"""
        session = self._get_session()
        try:
            conversations = session.query(Conversation).order_by(
                Conversation.updated_at.desc()
            ).all()

            return [conv.to_dict() for conv in conversations]
        except Exception as e:
            logger.error(f"获取对话列表失败: {e}")
            return []
        finally:
            session.close()

    def get_stale_conversations(self, hours: int = 3, max_active_count: int = 10) -> List[Dict]:
        """获取需要主动跟进的对话

        条件：
        1. 更新时间超过指定小时数（默认3小时）
        2. 主动激活次数不超过最大值（默认10次）

        Args:
            hours: 距离上次更新的小时数阈值
            max_active_count: 最大主动激活次数

        Returns:
            符合条件的对话记录列表
        """
        session = self._get_session()
        try:
            from datetime import timedelta
            time_threshold = datetime.now() - timedelta(hours=hours)

            conversations = session.query(Conversation).filter(
                Conversation.updated_at < time_threshold,
                Conversation.active_count < max_active_count
            ).all()

            result = [conv.to_dict() for conv in conversations]
            logger.info(f"找到 {len(result)} 个需要跟进的对话（更新时间>{hours}小时，激活次数<{max_active_count}）")
            return result
        except Exception as e:
            logger.error(f"查询待跟进对话失败: {e}")
            return []
        finally:
            session.close()