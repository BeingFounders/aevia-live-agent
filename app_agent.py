from telethon import TelegramClient
import asyncio
import time
import openai
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

# Cargar variables de entorno
load_dotenv()

async def agente_verifica_estado_usuario(api: TelegramAPI, usuario: str):

    memoria = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    # Inicializamos el LLM (OpenAI) con temperatura 0.5 para respuestas naturales.
    llm = ChatOpenAI(
        model="gpt-4-turbo",
        temperature=0.5,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )

    # Contador de intentos sin respuesta
    intentos_sin_respuesta = 0
    max_intentos_sin_respuesta = 3  # En el tercer intento se dará por terminado el proceso

    resultado = None

    # Mensaje inicial de presentación
    primer_mensaje = f"Hola, {usuario} soy Avia, me contacto para ver si estás bien, ¿cómo te encuentras?"
    await api.send_msg(usuario, primer_mensaje)
    memoria.save_context({"input": ""}, {"output": primer_mensaje})

    # Espera inicial de 30 segundos
    await asyncio.sleep(30)

    while True:
        respuesta = await api.receive_msg(usuario)
        respuesta = respuesta.strip()
        print(f"[Contacto] Respuesta recibida: {respuesta}")

        if not respuesta or respuesta == "No hay mensaje previo guardado para comparar.":
            intentos_sin_respuesta += 1
            print(f"[Agente] No se recibió respuesta. Intento {intentos_sin_respuesta} de {max_intentos_sin_respuesta}")

            if intentos_sin_respuesta == 1:
                # Primer mensaje de preocupación
                prompt_llm_preocupacion = (
                    f"Eres Avia, una asistente virtual amable y empática. Notaste que {usuario} no ha respondido a mi saludo. "
                    f"Genera un mensaje que exprese preocupación y pregunte si está bien, de manera natural y empática."
                )
                mensaje_agente = llm.invoke(prompt_llm_preocupacion).content.strip()
                print(f"[Agente] Enviando mensaje de preocupación: {mensaje_agente}")
                await api.send_msg(usuario, mensaje_agente)
                memoria.save_context({"input": ""}, {"output": mensaje_agente})

            elif intentos_sin_respuesta == 2:
                # Segundo mensaje de preocupación, indicando que se contactará al contacto de emergencia
                prompt_llm_emergencia = (
                    f"Eres Aevia, una asistente virtual encargada de contactar a {usuario} periodicamente"
                    f"Genera un mensaje que exprese una gran preocupación porque no contestas sus mensajes"
                    f"indicando que pensas que puede haberte pasado algo malo y no vas a esperar mas y vas a contactar a tu contacto de emergencia. El mensaje debe serfirme, en lenguaje natura como un whatsapp."
                )
                mensaje_agente = llm.invoke(prompt_llm_emergencia).content.strip()
                print(f"[Agente] Enviando mensaje de emergencia: {mensaje_agente}")
                await api.send_msg(usuario, mensaje_agente)
                memoria.save_context({"input": ""}, {"output": mensaje_agente})

            elif intentos_sin_respuesta >= max_intentos_sin_respuesta:
                resultado = "El contacto no respondió varios mensajes"
                break

        else:
            # Si se recibe respuesta, se resetea el contador de intentos
            intentos_sin_respuesta = 0
            memoria.save_context({"input": respuesta}, {"output": ""})

            # Análisis de la respuesta para determinar el estado del usuario
            prompt_analisis = (
                f"Analiza la siguiente respuesta y determina si indica algo sobre el estado de {usuario}.\n"
                f"Respuesta del contacto: '{respuesta}'\n\n"
                f"Responde SOLO con una de estas opciones:\n"
                f"MAL - si la respuesta indica que la persona está mal\n"
                f"BIEN - si la respuesta indica que la persona está bien\n"
            )
            estado = llm.invoke(prompt_analisis).content.strip()
            print(f"[Agente] Estado: {estado}")

            if estado == "MAL":
                resultado = "El usuario está mal"
                mensaje_final = "Lamento mucho escuchar que estés mal, espero que te sientas mejor pronto."
                await api.send_msg(usuario, mensaje_final)
                print("protocolo vivo")
                break

            elif estado == "BIEN":
                resultado = "El usuario está bien"
                mensaje_final = "Me alegro de escuchar eso. Gracias por la información."
                await api.send_msg(usuario, mensaje_final)
                print("protocolo vivo")
                break

            else:
                # Si no queda claro, se continúa la conversación usando el historial de mensajes.
                prompt_llm = (
                    f"Eres Avia, una asistente virtual amable y empática. Tu objetivo es averiguar si {usuario} "
                    f"está vivo o falleció, pero debes hacerlo de manera sensible y natural.\n\n"
                    f"Contexto: Estás hablando con un contacto para verificar el estado de {usuario}. "
                    f"Basándote en la siguiente conversación, genera una respuesta apropiada.\n"
                    f"Historial de conversación:\n{memoria.load_memory_variables({})['chat_history']}\n\n"
                    f"Genera una respuesta natural y apropiada para continuar la conversación."
                )
                
                mensaje_agente = llm.invoke(prompt_llm).content.strip()
                print(f"[Agente] Enviando mensaje: {mensaje_agente}")
                await api.send_msg(usuario, mensaje_agente)
                memoria.save_context({"input": ""}, {"output": mensaje_agente})

        # Se espera 30 segundos antes de volver a intentar recibir un mensaje
        await asyncio.sleep(30)
        
        messages = memoria.load_memory_variables({})["chat_history"]
        if len(messages) > 20:
            print("[Agente] Demasiados mensajes sin una respuesta concluyente. Se detiene el proceso.")
            resultado = "El contacto no respondió varios mensajes"
            print("protocolo contacto emergencia")
            break

    print("\n===== RESULTADO FINAL =====")
    print(resultado)






# --- Función del agente usando LangChain con memoria ---
async def agente_verifica_estado_emergency(api: TelegramAPI, contacto_id: str, usuario: str):
    """
    Función asíncrona que implementa el agente.
    Envía mensajes al contacto y, según las respuestas,
    determina si:
      1) El usuario falleció.
      2) El usuario está vivo.
      3) El contacto no respondió varios mensajes.
    Se espera 30 segundos entre mensajes.
    """
    memoria = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    # Inicializamos el LLM (OpenAI) con temperatura 0 para respuestas deterministas.
    llm = ChatOpenAI(
        model="gpt-4-turbo",
        temperature=0.5,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )

    
    # Contadores para detectar falta de respuesta
    intentos_sin_respuesta = 0
    max_intentos_sin_respuesta = 3

    resultado = None
    
    # Mensaje inicial de presentación
    primer_mensaje = (
        f"Hola, soy Avia, una asistente virtual. Estoy tratando de verificar información "
        f"sobre {usuario}. ¿Podrías ayudarme?"
    )
    
    await api.send_msg(contacto_id, primer_mensaje)
    memoria.save_context({"input": ""}, {"output": primer_mensaje})
    
    await asyncio.sleep(30)
    
    while True:
        respuesta = await api.receive_msg(contacto_id)
        respuesta = respuesta.strip()
        print(f"[Contacto] Respuesta recibida: {respuesta}")
        
        if not respuesta or respuesta == "No hay mensaje previo guardado para comparar.":
            intentos_sin_respuesta += 1
            print(f"[Agente] No se recibió respuesta. Intento {intentos_sin_respuesta} de {max_intentos_sin_respuesta}")
            if intentos_sin_respuesta >= max_intentos_sin_respuesta:
                resultado = "El contacto no respondió varios mensajes"
                break
        else:
            intentos_sin_respuesta = 0
            memoria.save_context({"input": respuesta}, {"output": ""})
            
            # Primero, analizar si la respuesta indica algo sobre el estado del usuario
            prompt_analisis = (
                f"Analiza la siguiente respuesta y determina si indica algo sobre el estado de {usuario}.\n"
                f"Respuesta del contacto: '{respuesta}'\n\n"
                f"Responde SOLO con una de estas opciones:\n"
                f"FALLECIDO - si la respuesta indica que la persona falleció\n"
                f"VIVO - si la respuesta indica que la persona está viva\n"
                f"NO_CLARO - si la respuesta no es clara o no indica nada sobre el estado de la persona"
            )
            estado = llm.invoke(prompt_analisis).content.strip()
            print(f"[Agente] Estado: {estado}")
            if estado == "FALLECIDO":
                resultado = "El usuario falleció"
                mensaje_final = "Lamento mucho escuchar eso. Gracias por la información. Mis condolencias."
                await api.send_msg(contacto_id, mensaje_final)
                print("protocolo fallecido")
                break
            elif estado == "VIVO":
                resultado = "El usuario está vivo"
                mensaje_final = "Me alegro de escuchar eso. Gracias por la información."
                await api.send_msg(contacto_id, mensaje_final)
                print("protocolo vivo")
                break
            else:
                # Si no está claro, continuar la conversación
                prompt_llm = (
                    f"Eres Avia, una asistente virtual amable y empática. Tu objetivo es averiguar si {usuario} "
                    f"está vivo o falleció, pero debes hacerlo de manera sensible y natural.\n\n"
                    f"Contexto: Estás hablando con un contacto para verificar el estado de {usuario}. "
                    f"Basándote en la siguiente conversación, genera una respuesta apropiada.\n"
                    f"Historial de conversación:\n{memoria.load_memory_variables({})['chat_history']}\n\n"
                    f"Genera una respuesta natural y apropiada para continuar la conversación."
                )
                
                mensaje_agente = llm.invoke(prompt_llm).content.strip()
                print(f"[Agente] Enviando mensaje: {mensaje_agente}")
                
                await api.send_msg(contacto_id, mensaje_agente)
                memoria.save_context({"input": ""}, {"output": mensaje_agente})

        await asyncio.sleep(30)
        
        messages = memoria.load_memory_variables({})["chat_history"]
        print(estado)
        if estado != "NO_CLARO":
            print("final iteraccion")
            break
        if len(messages) > 20:
            print("[Agente] Demasiados mensajes sin una respuesta concluyente. Se detiene el proceso.")
            resultado = "El contacto no respondió varios mensajes"
            break

    print("\n===== RESULTADO FINAL =====")
    print(resultado)



# Función modificada para notificar el fallecimiento de "usuario" al "beneficiario" y comunicarle el legado.
async def agente_notifica_fallecimiento(api: TelegramAPI, usuario: str, beneficiario: str, legado: str):
    # Mensaje inicial de notificación al beneficiario
    mensaje_inicial = (
        f"Hola, {beneficiario}, soy Avia. Lamento informarte que {usuario} ha fallecido. "
        f"Antes de partir, {usuario} te dejó un legado: {legado}. "
        f"Estoy aquí para ayudarte con lo que necesites respecto a este legado."
    )
    await api.send_msg(beneficiario, mensaje_inicial)
    print("Notificación enviada al beneficiario.")










# Definir el modelo de datos para la solicitud
class UserRequest(BaseModel):
    contacto_id: str
    usuario: str

class UserRequest_user_status(BaseModel):
    usuario: str

class UserRequest_beneficiary_notification(BaseModel):
    usuario: str
    beneficiario: str
    legado: str


app = FastAPI()

# Configuración global de Telegram
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
telegram_api = TelegramAPI(API_ID, API_HASH)

@app.on_event("startup")
async def startup_event():
    await telegram_api.client.start()

@app.on_event("shutdown")
async def shutdown_event():
    await telegram_api.client.disconnect()

async def start_conversation_emergency_contact(contacto_id: str, usuario: str):
    """
    Función que maneja la conversación en segundo plano
    """
    await agente_verifica_estado_emergency(telegram_api, contacto_id, usuario)

@app.post("/start_conversation_emergency_contact/")
async def start_conversation_emergency_contact_bk(user: UserRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(start_conversation_emergency_contact, user.contacto_id, user.usuario)
    return {
        "message": f"Iniciada la conversación para verificar el estado de {user.usuario} con el contacto {user.contacto_id}"
    }


async def start_conversation_user_status(usuario: str):
    """
    Función que maneja la conversación en segundo plano
    """
    await agente_verifica_estado_usuario(telegram_api, usuario)

@app.post("/start_conversation_user_status/")
async def start_conversation_user_status_bk(user: UserRequest_user_status, background_tasks: BackgroundTasks):
    background_tasks.add_task(start_conversation_user_status,user.usuario)
    return {
        "message": f"Iniciada la conversación para verificar el estado de {user.usuario}"
    }

async def start_conversation_beneficiary_notification(usuario: str, beneficiario: str, legado: str):
    """
    Función que maneja la conversación en segundo plano
    """
    await agente_notifica_fallecimiento(telegram_api, usuario, beneficiario, legado)

@app.post("/start_conversation_beneficiary_notification/")
async def start_conversation_beneficiary_notification_bk(user: UserRequest_beneficiary_notification, background_tasks: BackgroundTasks):
    background_tasks.add_task(start_conversation_beneficiary_notification,user.usuario, user.beneficiario, user.legado)
    return {
            "message": f"Iniciada la conversación para notificar el fallecimiento de {user.usuario} al beneficiario {user.beneficiario}"
    }






# Ejecutar la aplicación
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
