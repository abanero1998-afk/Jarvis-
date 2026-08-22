#!/usr/bin/env python3
import json, os, re, time, urllib.request
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
try:
    from groq import Groq
except ImportError:
    Groq = None
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
SB_URL = os.getenv("SUPABASE_URL", "https://qnpdilurpkjsqloznmko.supabase.co")
SB_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_VbIkIFYgrPzic5nXJXISZw_Q9LIhN--")
GEST = "https://gestionaletestematte.netlify.app/"
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
groq = Groq(api_key=GROQ_API_KEY) if Groq and GROQ_API_KEY else None
_cache = {"t": 0, "menu": []}
class ChatIn(BaseModel):
    message: str
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
def load_menu():
    now = time.time()
    if _cache["menu"] and now - _cache["t"] < 120:
        return _cache["menu"]
    menu = []
    try:
        html = urllib.request.urlopen(GEST, timeout=15).read().decode("utf-8", "replace")
        for a,b,c,d,e in re.findall(r'\{id:"([^"]+)", name:"([^"]+)", desc:"([^"]*)", price:([0-9.]+), type:"([^"]+)"', html):
            menu.append({"id": a, "name": b, "desc": c, "price": float(d), "type": e})
    except Exception:
        pass
    try:
        rows = sb_get("/rest/v1/tm_custom?id=eq.main&select=data")
        custom = (rows[0].get("data") if rows else []) or []
        for p in custom:
            menu.append({"id": p.get("id"), "name": p.get("name"), "desc": p.get("desc") or "", "price": float(p.get("price") or 0), "type": p.get("type") or "food"})
    except Exception:
        pass
    _cache["menu"] = menu
    _cache["t"] = now
    return menu
def norm(s):
    s = (s or "").lower()
    s = s.replace("à","a").replace("è","e").replace("é","e").replace("ì","i").replace("ò","o").replace("ù","u")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()
def search_product(q):
    nq = norm(q)
    if not nq: return None
    best = None
    best_score = 0
    for p in load_menu():
        nn = norm(p.get("name"))
        if not nn: continue
        score = 0
        if nq == nn: score = 100
        elif nq in nn or nn in nq: score = 80
        else:
            words = [w for w in nq.split() if len(w) > 2]
            if words and all(w in nn for w in words): score = 70
        if score > best_score:
            best_score = score
            best = p
    return best if best_score >= 70 else None
def table_id(num):
    t = str(num or "").strip().lower().replace("tavolo", "").replace("table", "").strip()
    if t in ("bancone", "bar"): return "BAR", "Bancone"
    if t.startswith("d") or "dehors" in t:
        d = re.search(r"(\d+)", t)
        n = d.group(1) if d else "1"
        return "D"+n, "Dehors "+n
    d = re.search(r"(\d+)", t)
    n = d.group(1) if d else "1"
    return "T"+n, "T"+n
def same_day(iso):
    if not iso: return False
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return d.date() == datetime.now(timezone.utc).date()
    except Exception:
        return False
def open_order_for(tid):
    for o in load_orders():
        if str(o.get("tableId")) == tid and o.get("status") not in ("pagato", "annullato", "chiuso"):
            return o
    return None
def open_table(tid, tname):
    existing = open_order_for(tid)
    if existing: return existing, False
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    order = {"id": "ord_" + hex(int(time.time()*1000))[2:], "items": [], "total": 0, "paidAt": None, "status": "in_corso", "readyAt": None, "tableId": tid, "servedAt": None, "createdAt": now, "tableName": tname, "destination": "cucina"}
    data = load_orders(); data.append(order); save_orders(data)
    return order, True
def add_item(tid, product, qty=1):
    data = load_orders()
    target = None
    for o in data:
        if str(o.get("tableId")) == tid and o.get("status") not in ("pagato", "annullato", "chiuso"):
            target = o; break
    if not target:
        order, _ = open_table(tid, tid)
        data = load_orders()
        for o in data:
            if o.get("id") == order["id"]:
                target = o; break
    item = {"qty": int(qty or 1), "name": product["name"], "type": product.get("type") or "food", "price": float(product["price"]), "variant": "", "productId": product["id"]}
    target.setdefault("items", []).append(item)
    target["total"] = sum(float(i.get("price") or 0) * int(i.get("qty") or 1) for i in target["items"])
    save_orders(data)
    return target
def split_products(chunk):
    chunk = re.sub(r"\bal tavolo\b.*", "", chunk, flags=re.I)
    chunk = re.sub(r"\btavolo\s*\d+\b", "", chunk, flags=re.I)
    chunk = re.sub(r"\bt\s*\d+\b", "", chunk, flags=re.I)
    parts = re.split(r"\s+e\s+|,\s*", chunk)
    out = []
    for p in parts:
        p = re.sub(r"^(aggiungi|metti|manda|invia|apri)\s+", "", p.strip(), flags=re.I).strip(" .")
        if p: out.append(p)
    return out
def cassiere(text):
    t = (text or "").strip(); low = t.lower()
    if any(k in low for k in ("incass", "fatturat")) or ("quanto" in low and "oggi" in low):
        orders = load_orders()
        today = [o for o in orders if same_day(o.get("createdAt")) or same_day(o.get("paidAt"))]
        paid = [o for o in today if o.get("status") == "pagato" or o.get("paidAt")]
        tot = sum(float(o.get("total") or 0) for o in paid)
        return f"Oggi {len(paid)} scontrini pagati, incasso {tot:.2f} euro."
    if low in ("tavoli", "elenco tavoli", "stato tavoli"):
        opened = [o for o in load_orders() if o.get("status") not in ("pagato", "annullato", "chiuso")]
        if not opened: return "Nessun tavolo aperto."
        return "Tavoli aperti: " + ", ".join(f"{o.get('tableName')} ({o.get('total')}€)" for o in opened[:20])
    m_tav = re.search(r"(?:tavolo|t)\s*(\d+)|bancone|dehors\s*(\d+)", low)
    want_open = bool(re.search(r"\b(aggiungi tavolo|apri tavolo|apri t\s*\d+|tavolo\s*\d+)\b", low))
    want_add = bool(re.search(r"\b(aggiungi|metti|manda|invia)\b", low)) and bool(m_tav)
    if m_tav:
        tid, tname = table_id(m_tav.group(0))
    else:
        tid = tname = None
    if want_open and tid and not re.search(r"aggiungi .+\s+(al\s+)?tavolo", low):
        only_table = not re.search(r"aggiungi\s+(?!tavolo)([a-z].+)", low)
        if only_table or low.startswith("apri") or low.startswith("aggiungi tavolo"):
            order, created = open_table(tid, tname)
            return f"Tavolo {tname} aperto. Pronto per ordine." if created else f"Tavolo {tname} già aperto. Pronto per ordine."
    if want_add and tid:
        phrase = re.sub(r"aggiungi\s+tavolo\s+\d+,?\s*", "", t, flags=re.I)
        phrase = re.sub(r"\b(al\s+)?tavolo\s*\d+\b", "", phrase, flags=re.I)
        phrase = re.sub(r"\bt\s*\d+\b", "", phrase, flags=re.I)
        names = split_products(phrase)
        if not names:
            open_table(tid, tname)
            return f"Tavolo {tname} aperto. Dimmi i prodotti da aggiungere."
        found, missing = [], []
        for n in names:
            p = search_product(n)
            if p: found.append(p)
            else: missing.append(n)
        if missing:
            return "ERRORE: " + ", ".join(missing) + " non trovato nel gestionale. Vuoi che avviso in cucina?"
        open_table(tid, tname)
        last = None; lines = []
        for p in found:
            last = add_item(tid, p, 1)
            lines.append(f"1x {p['name']} ({p['price']:.2f}€)")
        tot = last.get("total") if last else 0
        return f"Fatto. Tavolo {tname}: " + ", ".join(lines) + f". Totale parziale: {tot:.2f}€"
    if want_open and tid:
        order, created = open_table(tid, tname)
        return f"Tavolo {tname} aperto. Pronto per ordine." if created else f"Tavolo {tname} già aperto."
    return None
def pensa(text):
    c = cassiere(text)
    if c: return c
    if not groq:
        return "Dimmi: aggiungi tavolo 1, oppure aggiungi coca cola al tavolo 1."
    try:
        r = groq.chat.completions.create(model="openai/gpt-oss-20b", messages=[{"role":"system","content":"Cassiere Teste Matte. ZERO invenzione. Se il piatto non e nel menu rispondi errore."},{"role":"user","content":text}], max_tokens=200)
        return r.choices[0].message.content or "Dimmi tavolo e prodotti."
    except Exception as e:
        return "Dimmi tavolo e prodotti."
@app.get("/health")
def health():
    return {"status":"ok","agent":"Jarvis Cassa","time": datetime.utcnow().isoformat()}
@app.get("/")
def root():
    return FileResponse("index.html") if os.path.exists("index.html") else health()
@app.get("/api/products/search")
def api_search(q: str = Query("")):
    p = search_product(q)
    return {"found": bool(p), "q": q, "product": p}
@app.get("/api/tables")
def api_tables():
    opened = [o for o in load_orders() if o.get("status") not in ("pagato","annullato","chiuso")]
    return {"aperti": [{"id": o.get("tableId"), "name": o.get("tableName"), "total": o.get("total"), "items": o.get("items")} for o in opened]}
@app.post("/chat")
def chat(body: ChatIn):
    text = (body.message or "").strip()
    if not text: return {"risposta": "Dimmi pure, signore."}
    try: return {"risposta": pensa(text)}
    except Exception as e: return {"risposta": "Errore cassa: " + str(e)[:200]}
