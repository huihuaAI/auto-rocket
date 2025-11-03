import aiohttp
import json
from typing import Dict, Any
from db_manager import ConversationManager

class DifyChatBot:
    def __init__(self, base_url: str, api_key: str, input_params:dict, db_path: str = "conversations.db"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.input_params = input_params
        self.conversation_id = None
        self.user = "测试Lambda"
        self.account_id = None
        self.friend_id = None
        self.chat_user_id = None
        self.conversation_manager = ConversationManager(db_path)
        self._load_conversation_id()

    async def _make_request(self, endpoint: str, data: Dict[Any, Any], stream: bool = False):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        url = f"{self.base_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                response.raise_for_status()
                if stream:
                    return response, session
                else:
                    result = await response.json()
                    return result

    async def chat_completion(self, message: str, files: list = None, stream: bool = False) -> Dict[Any, Any]:
        """发送消息到 Dify，支持 blocking 和 streaming 模式"""
        data = {
            "inputs": self.input_params,
            "query": message if message else  " ",
            "response_mode": "streaming" if stream else "blocking",
            "user": self.user
        }
        if files:
            data["files"] = files

        if self.conversation_id:
            data["conversation_id"] = self.conversation_id
        if stream:
            return await self._handle_stream_response(data)
        else:
            result = await self._make_request("/chat-messages", data, stream=False)
            if not result:
                return {"answer": "⚠️ 空响应", "conversation_id": None, "message_id": None}

            answer = (
                result.get("answer")
                or result.get("output_text")
                or result.get("outputs", {}).get("text")
                or json.dumps(result, ensure_ascii=False)
            )

            conv_id = result.get("conversation_id")
            msg_id = result.get("id")

            if conv_id:
                self._save_conversation_id(conv_id)

            return {
                "answer": answer,
                "conversation_id": conv_id,
                "message_id": msg_id,
            }

    async def _handle_stream_response(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        full_response = ""
        conversation_id = None
        message_id = None

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        url = f"{self.base_url}/chat-messages"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                response.raise_for_status()
                async for line in response.content:
                    if not line:
                        continue
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        try:
                            data_json = json.loads(line_str[6:])
                            if data_json.get('event') == 'message':
                                full_response += data_json.get('answer', '')
                                conversation_id = conversation_id or data_json.get('conversation_id')
                                message_id = message_id or data_json.get('id')
                            elif data_json.get('event') == 'message_end':
                                break
                        except json.JSONDecodeError:
                            continue

        if conversation_id:
            self._save_conversation_id(conversation_id)

        return {
            "answer": full_response,
            "conversation_id": conversation_id,
            "message_id": message_id
        }

    async def get_conversation_history(self) -> Dict[Any, Any]:
        if not self.conversation_id:
            return {"messages": []}
        params = {"account_id": self.account_id, "friend_id": self.friend_id, "conversation_id": self.conversation_id}
        headers = {'Authorization': f'Bearer {self.api_key}'}
        url = f"{self.base_url}/messages"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                response.raise_for_status()
                return await response.json()

    def _load_conversation_id(self):
        saved_conversation_id = self.conversation_manager.get_conversation_id(self.chat_user_id)
        if saved_conversation_id:
            self.conversation_id = saved_conversation_id
            print(f"已加载对话ID: {self.conversation_id}")
        else:
            print("未找到已有对话，将创建新对话")
            self.conversation_id = ""

    def _save_conversation_id(self, conversation_id: str):
        if conversation_id and conversation_id != self.conversation_id:
            self.conversation_id = conversation_id
            self.conversation_manager.save_conversation_id(self.chat_user_id, self.account_id, self.friend_id, conversation_id)
            print(f"已保存对话ID: {conversation_id}")

    def set_user(self, chat_user_id: str, account_id: str, friend_id: str):
        self.chat_user_id = chat_user_id
        self.account_id = account_id
        self.friend_id = friend_id
        self._load_conversation_id()

    def reset_conversation(self):
        if self.conversation_id:
            self.conversation_manager.delete_conversation(self.chat_user_id)
        self.conversation_id = None
        print(f"已重置用户 {self.account_id} 与好友 {self.friend_id} 的对话")

    def update_time(self):
        self.conversation_manager.update_timestamp(self.chat_user_id)
