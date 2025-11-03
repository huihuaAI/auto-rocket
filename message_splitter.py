import logging
from typing import List

logger = logging.getLogger(__name__)

class MessageSplitter:

    def __init__(self, delimiter: str = "&&&"):
        self.delimiter = delimiter
    
    def split_message(self, message: str) -> List[str]:
        if not message:
            logger.warning("收到空消息，无需分段")
            return []

        if self.delimiter not in message:
            logger.info(f"消息中不包含分隔符 '{self.delimiter}'，直接返回原消息")
            return [message]
        
        # 按分隔符分句
        segments = message.split(self.delimiter)
        
        # 分句清洗
        segments = [seg.strip() for seg in segments if seg.strip()]

        logger.info(f"消息已分段，共 {len(segments)} 段")

        return segments