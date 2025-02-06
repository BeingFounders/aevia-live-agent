from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv
import httpx
import asyncio

load_dotenv()

app = FastAPI()

class ProtocolRequest(BaseModel):
    user: str
    beneficiary: str
    legacy: str
    contact_id: str


@app.post("/start_cron")
async def start_cron(request: ProtocolRequest):
    try:
        await call_agent_api("user", request.user, request.beneficiary, request.legacy, request.contact_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/alive_protocol")
async def handle_alive_protocol(request: ProtocolRequest):
    print("alive protocol")
    try:
        return {
            "status": "success",
            "message": f"Alive protocol executed for user {request.user}",
            "protocol": "alive"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/emergency_protocol")
async def handle_emergency_protocol(request: ProtocolRequest):
    print("emergency protocol")
    try:
        await call_agent_api("emergency", request.user, request.beneficiary, request.legacy, request.contact_id)
        return {"status": "success", "message": "Emergency protocol initiated"}
    except Exception as e:
        print(f"Error en handle_emergency_protocol: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test")
async def test(user: str):
    print(user)



@app.post("/dead_protocol")
async def handle_dead_protocol(request: ProtocolRequest):
    print("dead protocol")
    try:
        await call_agent_api("beneficiary", request.user, request.beneficiary, request.legacy, request.contact_id)
        return {
            "status": "success",
            "message": f"Dead protocol executed for user {request.user} with contact {request.contact_id}",
            "protocol": "dead"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def call_agent_api(status_agent: str, user: str, beneficiary: str, legacy: str, contact_id: str):
    print("call_agent_api")
    async with httpx.AsyncClient() as client:
        data = {
            "user": user,
            "beneficiary": beneficiary,
            "legacy": legacy,
            "contact_id": contact_id,
            "status_agent": status_agent
        }
        try:
            response = await client.post(
                f"http://localhost:8000/start_conversation_{status_agent}/", 
                json=data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Error haciendo la petición: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error al conectar con el servicio: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            print(f"Error en la respuesta HTTP: {str(e)}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error del servicio interno: {str(e)}"
            )
        except Exception as e:
            print(f"Error inesperado: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error inesperado: {str(e)}"
            )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 