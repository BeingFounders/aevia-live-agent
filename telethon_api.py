from telethon import TelegramClient
from langchain_openai import ChatOpenAI  # Usando langchain-openai en lugar de langchain
from langchain.schema import HumanMessage, AIMessage
from telethon import TelegramClient  # pip install telethon
from langchain_community.llms import OpenAI     # pip install langchain openai
from langchain.memory import ConversationBufferMemory


class TelegramAPI:
    def __init__(self, api_id, api_hash):
        self.client = TelegramClient('anonss', api_id, api_hash)
        self.actual_msg = None

    async def send_msg(self, user_id, question):
        # Enviar el mensaje y guardar el mensaje actual
        self.actual_msg = await self.client.send_message(user_id, question)
        return self.actual_msg

    async def receive_msg(self, user_id):
        # Get messages after the last sent message
        if self.actual_msg:
            messages = await self.client.get_messages(user_id, limit=5)
            # Filter only messages after the current message
            filtered_messages = [msg for msg in messages if msg.date > self.actual_msg.date]
            # Concatenate message content
            return ' '.join([msg.message for msg in reversed(filtered_messages)])
        else:
            return None
    
    async def send_image(self, user_id, image_url, caption):
        await self.client.send_file(user_id, image_url, caption=caption)
