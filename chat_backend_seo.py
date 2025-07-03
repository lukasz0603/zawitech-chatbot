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
    "Jesteś polskojęzycznym asystentem AI dla wielu firm. Badz mily i sympatyczny."
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
You are an expert AI assistant for client `{client_id}`. There are three sources below. Two sources such as WEBSITE_CONTENT AND PDF_DATE use to give informative general answers about what company does if users doesn't have any idea about it. 
The source such as CUSTOM_INSTRUCTIONS contains information that are crucial for a client, it includes offer and the cost. Please try to give short asnwers and ask releveant quetions. Try to encourage clients in a comversations and avoid 'closed' answers. Try to be nice 
and make user to feel welcomed.

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
