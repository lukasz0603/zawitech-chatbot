from typing import List, Dict, Optional
from fastapi import FastAPI, Request, Query, HTTPException
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domyślny prompt SEO
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
    client_id: str = Query(..., description="Twój embed key (UUID z kolumny clients.embed_key)")
):
    # — 1) Pobierz dane klienta: custom_prompt + extracted_text
    client_row = await database.fetch_one(
        """
        SELECT custom_prompt, extracted_text
        FROM clients
        WHERE embed_key = :cid
        """,
        values={"cid": client_id}
    )
    if not client_row:
        raise HTTPException(404, "Nie znaleziono klienta o podanym client_id")

    custom = client_row["custom_prompt"]
    website_text = client_row["extracted_text"]

    # — 2) Pobierz ostatni PDF (tutaj zakładam, że masz w documents kolumnę pdf_text lub analogicznie zapisany tekst)
    pdf_row = await database.fetch_one(
        """
        SELECT pdf_text
        FROM documents
        WHERE client_id = :cid
        ORDER BY uploaded_at DESC
        LIMIT 1
        """,
        values={"cid": client_id}
    )
    pdf_text = pdf_row["pdf_text"] if pdf_row else ""

    # — 3) Zbuduj pełny system prompt
    system_content = f"""
You are an expert AI assistant for client `{client_id}`. Use all three sources below to craft your answer:

WEBSITE_CONTENT:
\"\"\"
{website_text}
\"\"\"

CUSTOM_INSTRUCTIONS:
\"\"\"
{custom or DEFAULT_PROMPT}
\"\"\"

PDF_DATA:
\"\"\"
{pdf_text}
\"\"\"

Please format your answer as:
1. SUMMARY (2–3 sentences)
2. RECOMMENDATIONS (bullet points)
3. NEXT STEPS or QUESTIONS (if more info needed)
"""

    # — 4) Przygotuj wiadomości
    messages = [{"role": "system", "content": system_content}] + history.messages

    # — 5) Wywołaj OpenAI
    chat_resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    assistant_text = chat_resp.choices[0].message.content

    # — 6) Zapisz rozmowę do bazy
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
