from typing import List, Dict
from fastapi import FastAPI, Request, Query, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import json
import databases

# Połączenie z bazą danych
DATABASE_URL = os.getenv("DATABASE_URL")
database = databases.Database(DATABASE_URL)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domyślny system prompt dla SEO
DEFAULT_PROMPT = (
    "Jesteś polskojęzycznym asystentem AI w firmie Zawitech, która oferuje profesjonalne usługi SEO. "
    "Najpierw zapytaj: Czy klient ma już stronę internetową? Czy działa lokalnie, ogólnopolsko czy międzynarodowo? "
    "Jakie ma cele (więcej odwiedzin, sprzedaż)? Jaki ma budżet? "
    "Następnie zaproponuj jeden z trzech pakietów SEO: START (3000 PLN), STANDARD (5000 PLN), PREMIUM (7000 PLN). "
    "Umowa: czas nieokreślony, 1 mies. wypowiedzenia."
)

class ChatHistory(BaseModel):
    messages: List[Dict[str, str]]

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/chat")
async def chat(
    request: Request,
    history: ChatHistory,
    client_id: str = Query(..., description="Twój klucz embed dla danego klienta")
):
    # 1) pobierz custom_prompt z tabeli users
    row = await database.fetch_one(
        "SELECT custom_prompt FROM users WHERE embed_key = :ek",
        values={"ek": client_id}
    )
    if not row:
        raise HTTPException(404, detail="Nie znaleziono klienta o podanym client_id")

    system_content = row["custom_prompt"] or DEFAULT_PROMPT

    # 2) zbuduj wiadomości
    messages = [{"role": "system", "content": system_content}] + history.messages

    # 3) wywołaj OpenAI
    chat_resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    assistant_text = chat_resp.choices[0].message.content

    # 4) zapisz do bazy z client_id i IP
    try:
        await database.execute(
            """
            INSERT INTO chats (client_id, messages, ip_address)
            VALUES (:cid, :msgs, :ip)
            """,
            values={
                "cid": client_id,
                "msgs": json.dumps(history.messages + [{"role": "assistant", "content": assistant_text}]),
                "ip": request.client.host
            }
        )
    except Exception as e:
        print("❌ Błąd zapisu do bazy:", e)

    return {"response": assistant_text}
