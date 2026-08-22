#!/usr/bin/env python3
import json, os, re, time, urllib.request
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
try:
    from groq import Groq
except ImportError:
    Groq = None

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
SB_URL = os.getenv("SUPABASE_URL", "https://qnpdilurpkjsqloznmko.supabase.co")
SB_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_VbIkIFYgrPzic5nXJXISZw_Q9LIhN--")
SYS = "Sei Jarvis di Teste Matte. Italiano, diretto, stile Iron Man. Formato ANALISI/AZIONE/RISULTATO. Non inventare incassi."

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
groq = Groq(api_key=GROQ_API_KEY) if Groq and GROQ_API_KEY else None

class ChatIn(BaseModel):
    message: str
class ComandaIn(BaseModel):
    tavolo: str
    nome: str = ""
    qty: int = 1
    prezzo: float = 0

def hdr(extra=None):
    h = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY, "Content-Type": "application/json"}
    if extra: h.update(extra)
    return h

def sb_get(path):
    req = urllib.request.Request(SB_URL + path, headers=hdr())
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode())

def load_orders():
    rows = sb_get("/rest/v1/tm_orders?id=eq.main&select=data")
    data = (rows[0].get("data") if rows else []) or []
    return data if isinstance(data, list) else []

def save_orders(data):
    body = json.dumps({"data": data, "updated_at": datetime.now(timezone.utc).isoformat()}).encode()
    req = urllib.request.Request(SB_URL + "/rest/v1/tm_orders?id=eq.main", data=body, headers=hdr({"Prefer": "return=minimal"}), method="PATCH")
    with urllib.request.urlopen(req, timeout=12) as r:
        r.read()

def same_day(iso):
    if not iso: return False
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.date() == datetime.now(timezone.utc).date()
    except Exception:
        return False

def stato():
    orders = load_orders()
    today = [o for o in orders if same_day(o.get("createdAt")) or same_day(o.get("paidAt"))]
    paid = [o for o in today if o.get("status") == "pagato" or o.get("paidAt")]
    aperti = [o for o in orders if o.get("status") not in (None, "pagato", "annullato", "chiuso")]
    incasso = sum(float(o.get("total") or 0) for o in paid)
    tavoli = sorted({str(o.get("tableName") or o.get("tableId")) for o in orders if o.get("tableId") or o.get("tableName")})
    return {"ordini_oggi": len(today), "pagati_oggi": len(paid), "incasso_oggi": round(incasso, 2), "aperti": aperti, "tavoli": tavoli}

def nuova_comanda(tavolo, nome="", qty=1, prezzo=0.0):
    items = [{"qty": int(qty or 1), "name": nome or "Apertura tavolo", "type": "food", "price": float(prezzo or 0), "variant": "", "productId": ""}]
    total = sum(float(i["price"]) * int(i["qty"]) for i in items)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    tid = (tavolo or "T?").strip()
    order = {"id": "ord_" + hex(int(time.time()*1000))[2:], "items": items, "total": total, "paidAt": None, "status": "in_corso", "readyAt": None, "tableId": tid, "servedAt": None, "createdAt": now, "tableName": tid, "destination": "cucina"}
    data = load_orders(); data.append(order); save_orders(data)
    return order

def act(text):
    t = (text or "").lower().strip()
    st = stato()
    if any(k in t for k in ("incass", "fatturat")) or ("quanto" in t and "oggi" in t):
        return f"**ANALISI**: Incassi.\n**AZIONE**: Lettura gestionale.\n**RISULTATO**: Oggi {st['pagati_oggi']} scontrini, {st['incasso_oggi']:.2f} euro."
    if "tavol" in t and any(k in t for k in ("aggiungi", "apri", "nuovo", "crea")):
        m = re.search(r"(t\s?\d+|dehors\s?\d+|bancone)", t, re.I)
        name = m.group(1).replace(" ", "").upper() if m else "T" + str(len(st["tavoli"]) + 1)
        order = nuova_comanda(name, "Apertura tavolo")
        return f"**ANALISI**: Apertura tavolo.\n**AZIONE**: Scrittura gestionale.\n**RISULTATO**: Tavolo {order['tableName']} aperto ({order['id']})."
    if "tavol" in t:
        lista = ", ".join(st["tavoli"][:30]) or "nessuno"
        return f"**ANALISI**: Elenco tavoli.\n**AZIONE**: Storico ordini.\n**RISULTATO**: {len(st['tavoli'])} tavoli: {lista}."
    if "ordin" in t or ("comanda" in t and "manda" not in t and "invia" not in t):
        if not st["aperti"]:
            return "**ANALISI**: Comande.\n**AZIONE**: Lettura.\n**RISULTATO**: Nessun ordine aperto."
        pezzi = [f"{o.get('tableName')} {o.get('status')} {o.get('total')}e" for o in st["aperti"][:8]]
        return f"**ANALISI**: Comande aperte.\n**AZIONE**: Elenco.\n**RISULTATO**: {len(st['aperti'])}: " + "; ".join(pezzi)
    if any(k in t for k in ("manda", "invia")) or ("comanda" in t and "t" in t):
        m = re.search(r"(t\s?\d+)", t, re.I)
        tav = m.group(1).replace(" ", "").upper() if m else "T1"
        nome = text
        for cut in ("manda", "invia", "comanda", "aggiungi", "al tavolo", "tavolo", tav, tav.lower()):
            nome = re.sub(cut, " ", nome, flags=re.I)
        nome = " ".join(nome.split()).strip(" .") or "Piatto"
        order = nuova_comanda(tav, nome)
        return f"**ANALISI**: Comanda cucina.\n**AZIONE**: Scrittura su {tav}.\n**RISULTATO**: {order['id']} inviata: {nome}."
    return None

def pensa(user_text):
    a = act(user_text)
    if a: return a
    st = stato()
    ctx = f"Incasso oggi {st['incasso_oggi']} e. Pagati {st['pagati_oggi']}. Aperti {len(st['aperti'])}. Tavoli: {', '.join(st['tavoli'][:20])}."
    if not groq: return ctx
    try:
        r = groq.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"system","content":SYS},{"role":"user","content":"[Gestionale]\n"+ctx+"\n[Richiesta]\n"+user_text}], max_tokens=400)
        return r.choices[0].message.content or ctx
    except Exception as e:
        return ctx + " (" + str(e)[:100] + ")"

@app.get("/health")
def health():
    return {"status":"ok","agent":"Jarvis - Teste Matte","time": datetime.utcnow().isoformat()}

@app.get("/")
def root():
    return FileResponse("index.html") if os.path.exists("index.html") else health()

@app.get("/api/stato")
def api_stato():
    try: return stato()
    except Exception as e: return JSONResponse({"errore": str(e)}, status_code=500)

@app.post("/api/comanda")
def api_comanda(body: ComandaIn):
    try: return {"ok": True, "ordine": nuova_comanda(body.tavolo, body.nome, body.qty, body.prezzo)}
    except Exception as e: return JSONResponse({"ok": False, "errore": str(e)}, status_code=500)

@app.post("/chat")
def chat(body: ChatIn):
    text = (body.message or "").strip()
    if not text: return {"risposta": "Dimmi pure, signore."}
    try: return {"risposta": pensa(text)}
    except Exception as e: return {"risposta": "Errore: " + str(e)[:200]}
