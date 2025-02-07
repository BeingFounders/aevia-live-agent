from telethon import TelegramClient
import asyncio
import time
import openai
from openai import OpenAI
from langchain_openai import ChatOpenAI  # Usando langchain-openai en lugar de langchain
from langchain.schema import HumanMessage, AIMessage
from telethon import TelegramClient  # pip install telethon
from langchain_community.llms import OpenAI     # pip install langchain openai
from langchain.memory import ConversationBufferMemory
from telethon_api import TelegramAPI
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import httpx
from typing import Optional

# Cargar variables de entorno
load_dotenv()

async def agent_check_user_status(api: TelegramAPI, user: str, beneficiary: str, legacy: str, contact_id: str):
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    # Initialize LLM (OpenAI) with temperature 0.5 for natural responses
    llm = ChatOpenAI(
        model="gpt-4-turbo",
        temperature=0.5,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )

    # Counter for unanswered attempts
    unanswered_attempts = 0
    max_unanswered_attempts = 3

    result = None

    # Initial greeting message
    first_message = f"Hi {user}, I'm Aevia, I'm reaching out to check if you're okay. How are you feeling?"
    await api.send_msg(user, first_message)
    memory.save_context({"input": ""}, {"output": first_message})

    # Initial 30-second wait
    await asyncio.sleep(30)

    while True:
        response = await api.receive_msg(user)
        response = response.strip() if response else None
        print(f"[Contact] Response received: {response}")

        if not response:
            unanswered_attempts += 1
            print(f"[Agent] No response received. Attempt {unanswered_attempts} of {max_unanswered_attempts}")

            if unanswered_attempts == 1:
                # First concern message
                prompt_llm_concern = (
                    f"You are Aevia, a friendly and empathetic virtual assistant. You noticed that {user} hasn't responded to my greeting. "
                    f"Generate a message expressing concern and asking if they're okay, in a natural and empathetic way."
                )
                agent_message = llm.invoke(prompt_llm_concern).content.strip()
                print(f"[Agent] Sending concern message: {agent_message}")
                await api.send_msg(user, agent_message)
                memory.save_context({"input": ""}, {"output": agent_message})

            elif unanswered_attempts == 2:
                # Second concern message, indicating emergency contact will be notified
                prompt_llm_emergency = (
                    f"You are Aevia, a virtual assistant in charge of periodically contacting {user}. "
                    f"Generate a message expressing serious concern about their lack of response, "
                    f"indicating that you think something might be wrong and you'll be contacting their emergency contact. "
                    f"The message should be firm but natural, like a WhatsApp message."
                )
                agent_message = llm.invoke(prompt_llm_emergency).content.strip()
                print(f"[Agent] Sending emergency message: {agent_message}")
                await api.send_msg(user, agent_message)
                memory.save_context({"input": ""}, {"output": agent_message})

            elif unanswered_attempts >= max_unanswered_attempts:
                result = "Contact did not respond to multiple messages"
                print("emergency protocol")
                await call_protocol_api("emergency", user, beneficiary, legacy, contact_id)
                break

        else:
            # Reset attempt counter when response is received
            unanswered_attempts = 0
            memory.save_context({"input": response}, {"output": ""})

            # Analyze response to determine user's status
            prompt_analysis = (
                f"Analyze the following response and determine if it indicates anything about {user}'s status.\n"
                f"Contact's response: '{response}'\n\n"
                f"Respond ONLY with one of these options:\n"
                f"BAD - if the response indicates the person is not well\n"
                f"GOOD - if the response indicates the person is well\n"
            )
            status = llm.invoke(prompt_analysis).content.strip()
            print(f"[Agent] Status: {status}")

            if status == "BAD":
                result = "User is not well"
                final_message = "I'm sorry to hear you're not feeling well. I hope you feel better soon."
                await api.send_msg(user, final_message)
                print("alive protocol")
                await call_protocol_api("alive", user, beneficiary, legacy, contact_id)
                break

            elif status == "GOOD":
                result = "User is well"
                final_message = "I'm glad to hear that. Thank you for the information."
                await api.send_msg(user, final_message)
                await call_protocol_api("alive", user, beneficiary, legacy, contact_id)
                print("alive protocol")
                break

            else:
                # If not clear, continue conversation using message history
                prompt_llm = (
                    f"You are Aevia, a friendly and empathetic virtual assistant. Your goal is to determine if {user} "
                    f"is alive or deceased, but you must do it in a sensitive and natural way.\n\n"
                    f"Context: You are talking to a contact to verify {user}'s status. "
                    f"Based on the following conversation, generate an appropriate response.\n"
                    f"Conversation history:\n{memory.load_memory_variables({})['chat_history']}\n\n"
                    f"Generate a natural and appropriate response to continue the conversation."
                )
                
                agent_message = llm.invoke(prompt_llm).content.strip()
                print(f"[Agent] Sending message: {agent_message}")
                await api.send_msg(user, agent_message)
                memory.save_context({"input": ""}, {"output": agent_message})

        # Wait 30 seconds before trying to receive a message again
        await asyncio.sleep(30)
        
        messages = memory.load_memory_variables({})["chat_history"]
        if len(messages) > 20:
            print("[Agent] Too many messages without a conclusive response. Process stops.")
            result = "Contact did not respond to multiple messages"
            print("emergency contact protocol")
            await call_protocol_api("emergency", user, beneficiary, legacy, contact_id)
            break

    print("\n===== FINAL RESULT =====")
    print(result)






# --- Function of the agent using LangChain with memory ---
async def agent_check_user_status_emergency(api: TelegramAPI, user: str, beneficiary: str, legacy: str, contact_id: str):
    """
    Asynchronous function that implements the agent.
    Sends messages to the contact and, based on the responses,
    determines if:
      1) The user is deceased.
      2) The user is alive.
      3) The contact did not respond to multiple messages.
    Waits 30 seconds between messages.
    """
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    # Initialize LLM (OpenAI) with temperature 0 for deterministic responses.
    llm = ChatOpenAI(
        model="gpt-4-turbo",
        temperature=0.5,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )

    
    # Counters to detect lack of response
    unanswered_attempts = 0
    max_unanswered_attempts = 3

    result = None
    
    # Initial greeting message
    first_message = (
        f"Hi, I'm Aevia, a virtual assistant. I'm trying to verify information "
        f"about {user}. Could you help me?"
    )
    
    await api.send_msg(contact_id, first_message)
    memory.save_context({"input": ""}, {"output": first_message})
    
    await asyncio.sleep(30)
    
    while True:
        response = await api.receive_msg(contact_id)
        response = response.strip()
        print(f"[Contact] Response received: {response}")
        
        if not response or response == "No previous message stored for comparison.":
            unanswered_attempts += 1
            print(f"[Agent] No response received. Attempt {unanswered_attempts} of {max_unanswered_attempts}")
            if unanswered_attempts >= max_unanswered_attempts:
                result = "Contact did not respond to multiple messages"
                break
        else:
            unanswered_attempts = 0
            memory.save_context({"input": response}, {"output": ""})
            
            # First, analyze if the response indicates anything about the user's status
            prompt_analysis = (
                f"Analyze the following response and determine if it indicates anything about {user}'s status.\n"
                f"Contact's response: '{response}'\n\n"
                f"Respond ONLY with one of these options:\n"
                f"DECEASED - if the response indicates the person is deceased\n"
                f"ALIVE - if the response indicates the person is alive\n"
                f"NO_CLARO - if the response is unclear or does not indicate anything about the person's status"
            )
            status = llm.invoke(prompt_analysis).content.strip()
            print(f"[Agent] Status: {status}")
            if status == "DECEASED":
                result = "User is deceased"
                final_message = "I'm sorry to hear that. Thank you for the information. My condolences."
                await api.send_msg(contact_id, final_message)
                print("dead protocol")
                await call_protocol_api("dead", user, beneficiary, legacy, contact_id)
                break
            elif status == "ALIVE":
                result = "User is alive"
                final_message = "I'm glad to hear that. Thank you for the information."
                await api.send_msg(contact_id, final_message)
                print("alive protocol")
                await call_protocol_api("alive", user, beneficiary, legacy, contact_id)
                break
            else:
                # If not clear, continue the conversation
                prompt_llm = (
                    f"You are Aevia, a friendly and empathetic virtual assistant. Your goal is to determine if {user} "
                    f"is alive or deceased, but you must do it in a sensitive and natural way.\n\n"
                    f"Context: You are talking to a contact to verify {user}'s status. "
                    f"Based on the following conversation, generate an appropriate response.\n"
                    f"Conversation history:\n{memory.load_memory_variables({})['chat_history']}\n\n"
                    f"Generate a natural and appropriate response to continue the conversation."
                )
                
                agent_message = llm.invoke(prompt_llm).content.strip()
                print(f"[Agent] Sending message: {agent_message}")
                
                await api.send_msg(contact_id, agent_message)
                memory.save_context({"input": ""}, {"output": agent_message})

        await asyncio.sleep(30)
        
        messages = memory.load_memory_variables({})["chat_history"]
        print(status)
        if status != "NO_CLARO":
            print("final iteraccion")
            break
        if len(messages) > 20:
            print("[Agent] Too many messages without a conclusive response. Process stops.")
            result = "Contact did not respond to multiple messages"
            break

    print("\n===== FINAL RESULT =====")
    print(result)




# Function modified to notify the death of "user" to "beneficiary" and communicate the legacy.
async def agent_notify_death(api: TelegramAPI, user: str, beneficiary: str, legacy: str, contact_id: str):
    # Initial notification message to beneficiary
    initial_message = (
        f"Hi, {beneficiary}, I'm Aevia. I'm sorry to inform you that {user} has passed away. "
        f"Before leaving, {user} left you a legacy: {legacy}. "
        f"I'm here to help you with whatever you need regarding this legacy."
    )
    await api.send_msg(beneficiary, initial_message)
    print("Notification sent to beneficiary.")










# Define data model for request
class UserRequest(BaseModel):
    user: str
    beneficiary: str
    legacy: str
    contact_id: Optional[str] = None

app = FastAPI()

# Global configuration of Telegram
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
telegram_api = TelegramAPI(API_ID, API_HASH)

@app.on_event("startup")
async def startup_event():
    await telegram_api.client.start()

@app.on_event("shutdown")
async def shutdown_event():
    await telegram_api.client.disconnect()

async def start_conversation_emergency(status_agent: str, user: str, beneficiary: str, legacy: str, contact_id: str):
    """
    Function that handles conversation in the background
    """
    await agent_check_user_status_emergency(telegram_api, user, beneficiary, legacy, contact_id)

@app.post("/start_conversation_emergency/")
async def start_conversation_emergency_bk(user: UserRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        start_conversation_emergency, 
        "emergency",
        user.user, 
        user.beneficiary, 
        user.legacy, 
        user.contact_id
    )
    return {
        "message": f"Started conversation to verify status of {user.user} with contact {user.contact_id}"
    }

async def start_conversation_user(status_agent: str, user: str, beneficiary: str, legacy: str, contact_id: str):
    """
    Function that handles conversation in the background
    """
    await agent_check_user_status(telegram_api, user, beneficiary, legacy, contact_id)

@app.post("/start_conversation_user/")
async def start_conversation_user_bk(user: UserRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        start_conversation_user, 
        "user",
        user.user, 
        user.beneficiary, 
        user.legacy, 
        user.contact_id
    )
    return {
        "message": f"Started conversation to verify status of {user.user}"
    }

async def start_conversation_beneficiary(status_agent: str, user: str, beneficiary: str, legacy: str, contact_id: str):
    """
    Function that handles conversation in the background
    """
    await agent_notify_death(telegram_api, user, beneficiary, legacy, contact_id)

@app.post("/start_conversation_beneficiary/")
async def start_conversation_beneficiary_bk(user: UserRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        start_conversation_beneficiary, 
        "beneficiary",
        user.user, 
        user.beneficiary, 
        user.legacy, 
        user.contact_id
    )
    return {
        "message": f"Started conversation to notify death of {user.user} to beneficiary {user.beneficiary}"
    }



async def call_protocol_api(status_agent: str, user: str, beneficiary: str, legacy: str, contact_id: str = None):
    async with httpx.AsyncClient() as client:
        data = {
            "user": user,
            "beneficiary": beneficiary,
            "legacy": legacy,
            "contact_id": contact_id
        }
        response = await client.post(f"http://127.0.0.1:8001/{status_agent}_protocol", json=data)
        print(response.json())
        return response.json()

async def generate_memorial(user: str) -> str:
    print("generate_memorial")
    # Format username for URL
    encoded_user = user.replace(" ", "%20")
    
    # Get current date and 3 days ago
    from datetime import datetime, timedelta
    today = datetime.now()  
    three_days_ago = today - timedelta(days=120)
    
    # Format dates for URL
    from_date = three_days_ago.strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")
    
    # Make API request
    async with httpx.AsyncClient() as client:
        url = f"https://api.cookie.fun/v1/hackathon/search/rip%20{encoded_user}"
        headers = {
            "x-api-key": "481f5d6b-2a78-437f-835d-362352630fb9"
        }
        params = {
            "from": from_date,
            "to": to_date
        }
        
        response = await client.get(url, headers=headers, params=params)
        data = response.json()
        
        # Collect mentions in a list
        mentions = []
        if data.get("ok"):
            for item in data["ok"]:
                mentions.append({
                    "author": item["authorUsername"],
                    "text": item["text"]
                })
        
        # If no mentions found, return default message
        if not mentions:
            return f"No recent farewell messages were found for {user}."
        
        # Generate memorial using LLM
        llm = ChatOpenAI(
            model="gpt-4-turbo",
            temperature=0.7,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Create prompt for LLM
        mentions_text = "\n\n".join([f"@{m['author']}: {m['text']}" for m in mentions])
        prompt = f"""
        Generate a respectful and emotional memorial message for {user} based on the following social media messages. 
        The message should include user quotes and their messages, creating a narrative that honors their memory 
        and legacy.

        Messages:
        {mentions_text}
        """
        
        memorial_message = llm.invoke(prompt).content.strip()

        # Usar el cliente oficial de OpenAI para las imágenes
        from openai import OpenAI as OpenAIClient  # Renombramos para evitar conflictos
        
        client = OpenAIClient(api_key=os.getenv('OPENAI_API_KEY'))

        messageimg = f'''A respectful and serene tribute, based on the text below. dont include any text or number or faces, just an emotional representation {memorial_message}'''

        response = client.images.create(
            model="dall-e-3",
            prompt=messageimg,
            n=1,
            size="1024x1024",
            quality="standard"
        )

        # Mostrar las URLs generadas
        for i, image in enumerate(response.data):
            print(f"Imagen {i+1}: {image.url}")

        return memorial_message

class UserRequestMemorial(BaseModel):
    user: str

# Add new endpoint to generate memorial
@app.post("/generate_memorial/")
async def generate_memorial_endpoint(user: UserRequestMemorial):
    print("generate_memorial_endpoint")
    memorial = await generate_memorial(user.user)
    return {"memorial": memorial}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
