from typing import List, Dict
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
import json
import databases

DATABASE_URL = os.getenv("DATABASE_URL")
database = databases.Database(DATABASE_URL)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # lub ogranicz do Twoich domen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
async def chat(request: Request, history: ChatHistory):
    # 1) Sprawdź skąd pochodzi request (Origin lub Referer)
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        raise HTTPException(400, "Brak nagłówka Origin/Referer")

    # Upewnij się, że pasujesz format – np. bez końcowego '/'
    origin = origin.rstrip("/")

    # 2) Pobierz custom_prompt z bazy według tej strony
    row = await database.fetch_one(
        "SELECT custom_prompt FROM clients WHERE website = :website",
        values={"website": origin}
    )
    if not row or not row["custom_prompt"]:
        raise HTTPException(404, f"Nie znaleziono promptu dla strony {origin}")

    # 3) Zbuduj prompt dynamicznie
    system_prompt = {
        "role": "system",
        "content": row["custom_prompt"]
    }

    # 4) Kompletuj wiadomości i wywołaj OpenAI
    messages = [system_prompt] + history.messages
    chat_resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    response = chat_resp.choices[0].message.content

    # 5) Zapisz do historii
    try:
        await database.execute(
            """
            INSERT INTO chats (messages, ip_address)
            VALUES (:messages, :ip)
            """,
            values={
                "messages": json.dumps(history.messages + [{"role":"assistant","content":response}]),
                "ip": request.client.host
            }
        )
    except Exception:
        pass  # opcjonalnie loguj błąd

    return {"response": response}
