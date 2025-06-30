from typing import List, Dict
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import json
import databases

# Połączenie z bazą
DATABASE_URL = os.getenv("DATABASE_URL")
database = databases.Database(DATABASE_URL)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prompt
system_prompt = {
    "role": "system",
    "content": (
        "Jesteś polskojęzycznym asystentem AI w firmie Zawitech, która oferuje profesjonalne usługi SEO. "
        "Najpierw zapytaj: Czy klient ma już stronę internetową? Czy działa lokalnie, ogólnopolsko czy międzynarodowo? "
        "Jakie ma cele (więcej odwiedzin, sprzedaż)? Jaki ma budżet? "
        "Następnie zaproponuj jeden z trzech pakietów SEO: START (3000 PLN), STANDARD (5000 PLN), PREMIUM (7000 PLN). "
        "Umowa: czas nieokreślony, 1 mies. wypowiedzenia."
    )
}

# Model historii rozmowy
class ChatHistory(BaseModel):
    messages: List[Dict[str, str]]

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# 🔄 Główna trasa: dynamiczny client_id
@app.post("/chat/{client_id}")
async def chat(client_id: str, request: Request, history: ChatHistory):
    user_ip = request.client.host
    messages = [system_prompt] + history.messages

    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    response = chat.choices[0].message.content

    await database.execute(
        query="""
            INSERT INTO chats (client_id, messages, ip_address)
            VALUES (:client_id, :messages, :ip)
        """,
        values={
            "client_id": client_id,
            "messages": json.dumps(history.messages + [{"role": "assistant", "content": response}]),
            "ip": user_ip
        }
    )

    return {"response": response}
