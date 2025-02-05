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
        # Obtener los mensajes después del último mensaje enviado
        if self.actual_msg:
            messages = await self.client.get_messages(user_id, limit=5)
            # Filtrar solo los mensajes posteriores al mensaje actual
            filtered_messages = [msg for msg in messages if msg.date > self.actual_msg.date]
            # Concatenar el contenido de los mensajes
            return ' '.join([msg.message for msg in reversed(filtered_messages)])
        else:
            return "No hay mensaje previo guardado para comparar."