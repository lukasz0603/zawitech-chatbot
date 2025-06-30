from typing import List, Dict
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
from openai import OpenAI
from databases import Database  # <- tutaj dodajemy

# Inicjalizacja klienta OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Inicjalizacja FastAPI
app = FastAPI()

# Middleware CORS (dla frontendów)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Systemowy prompt do GPT
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

# Model danych dla wejścia
class ChatHistory(BaseModel):
    messages: List[Dict[str, str]]  # [{"role": "user", "content": "..."}]

# Endpoint główny
@app.post("/chat")
async def chat(history: ChatHistory):
    messages = [system_prompt] + history.messages

    chat = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    response_text = chat.choices[0].message.content


