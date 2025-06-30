from typing import List, Dict
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import json
import databases

# Połączenie z bazą danych (użyj swojego DATABASE_URL z Render)
DATABASE_URL = os.getenv("DATABASE_URL")  # <-- dodaj do środowiska!
database = databases.Database(DATABASE_URL)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Systemowy prompt
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

# Model danych
class ChatHistory(BaseModel):
    messages: List[Dict[str, str]]

# Połączenie z bazą na starcie
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Główna trasa chatu
@app.post("/chat")
async def chat(request: Request, history: ChatHistory):
    messages = [system_prompt] + history.messages

    # Odpowiedź od OpenAI
    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    response = chat.choices[0].message.content

    # Zapis do bazy danych (jako JSONB)
    await database.execute(
        query="INSERT INTO chats (messages) VALUES (:messages)",
        values={"messages": json.dumps(history.messages)}
    )

    return {"response": response}
  
