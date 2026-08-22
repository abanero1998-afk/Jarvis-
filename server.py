#!/usr/bin/env python3
"""Jarvis Web – cervello + UI. CORS aperto. Un solo servizio."""
import os
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

try:
    from groq import Groq
except ImportError:
    Groq = None

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://qnpdilurpkjsqloznmko.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_VbIkIFYgrPzic5nXJXISZw_Q9LIhN--")

SYSTEM = """Sei Jarvis, AI personale di Teste Matte.
Parli italiano. Diretto, efficiente, stile Iron Man.
Formato:
**ANALISI**: 1 riga
**AZIONE**: cosa fai
**RISULTATO**: cosa ottieni
Hai accesso al gestionale ristorante. Se chiedono incassi, ordini, tavoli, usa i dati forniti nel contesto.
"""

app = FastAPI(title="Jarvis Teste Matte")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=GROQ_API_KEY) if Groq and GROQ_API_KEY else None

class ChatIn(BaseModel):
    message: str

def gestionale_contesto() -> str:
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/tm_orders?id=eq.main&select=data",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode("utf-8")
        return raw[:4000]
    except Exception as e:
        return f"(gestionale non raggiungibile: {e})"

def pensa(user_text: str) -> str:
    if not groq_client:
        return "Cervello Groq non configurato. Imposta GROQ_API_KEY."
    ctx = gestionale_contesto()
    prompt = f"[Dati gestionale]\n{ctx}\n\n[Richiesta]\n{user_text}"
    try:
        resp = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=700,
        )
        return resp.choices[0].message.content or "Nessuna risposta."
    except Exception as e:
        return f"Errore cervello: {str(e)[:180]}"

@app.get("/health")
def health():
    return {"status": "ok", "agent": "Jarvis - Teste Matte", "time": datetime.utcnow().isoformat()}

@app.get("/")
def root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return health()

@app.post("/chat")
def chat(body: ChatIn):
    text = (body.message or "").strip()
    if not text:
        return {"risposta": "Dimmi pure, signore."}
    return {"risposta": pensa(text)}

@app.options("/chat")
def chat_options():
    return JSONResponse({"ok": True})
