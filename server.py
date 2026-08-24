#!/usr/bin/env python3
import json, os, re, time, urllib.request
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, JSONResponse
from pydantic import BaseModel
try:
    from groq import Groq
except ImportError:
    Groq = None
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_CHAT_MODEL = os.getenv("XAI_CHAT_MODEL", "grok-4.5")
XAI_IMAGE_MODEL = os.getenv("XAI_IMAGE_MODEL", "grok-imagine-image-2.0")
SB_URL = os.getenv("SUPABASE_URL", "https://qnpdilurpkjsqloznmko.supabase.co")
SB_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_VbIkIFYgrPzic5nXJXISZw_Q9LIhN--")
ELEVEN_KEY = os.getenv("ELEVEN_API_KEY", "sk_daea01152c06405ec898b07cb370c332caad93f03d11f8ca")
ELEVEN_VOICE = os.getenv("ELEVEN_VOICE_ID", "tkjyl8Joo8r3RALgNJDV")
WA_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WA_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WA_TO = os.getenv("WHATSAPP_TO", "393519667988")
GEST = "https://gestionaletestematte.netlify.app/"
SYS = (
    "Sei JARVIS, socio operativo di Mente Locale (https://mente-locale-premium.vercel.app/ + IG @smart.srls.ia). "
    "KPI: 1000 vendite entro 31/12/2026. Pacchetto minimo 1999 euro. Growth machine. Italiano, diretto. "
    "Post IG: Lun caso studio; Mar demo; Mer pain; Gio testimonial; Ven offerta 1999. "
    "Teste Matte: cassiere preciso, no piatti inventati, no incassi se non chiesti."
)
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
groq = Groq(api_key=GROQ_API_KEY) if Groq and GROQ_API_KEY else None
_cache = {"t": 0, "menu": []}
class ChatIn(BaseModel):
    message: str
class SpeakIn(BaseModel):
    text: str = ""
class ImageIn(BaseModel):
    prompt: str = ""
    theme: str = ""
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
def fix_stuck(data):
    changed = False
    for o in data:
        if o.get("status") == "in_corso":
            if o.get("items"):
                types = {(i.get("type") or "food") for i in o.get("items") or []}
                o["status"] = "inviato"
                o["destination"] = "bar" if types == {"beverage"} else "cucina"
            else:
                o["status"] = "pagato"
                o["paidAt"] = o.get("paidAt") or datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
            changed = True
    return changed
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
    _cache["menu"] = menu; _cache["t"] = now
    return menu
def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
def search_product(q):
    nq = norm(q)
    if not nq: return None
    best = None; best_score = 0
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
            best_score = score; best = p
    return best if best_score >= 70 else None
def table_id(num):
    t = str(num or "").strip().lower().replace("tavolo", "").replace("table", "").strip()
    if t in ("bancone", "bar"): return "BAR", "Bancone"
    if t.startswith("d") or "dehors" in t:
        d = re.search(r"(\d+)", t); n = d.group(1) if d else "1"
        return "D"+n, "Dehors "+n
    d = re.search(r"(\d+)", t); n = d.group(1) if d else "1"
    return "T"+n, "T"+n
def same_day(iso):
    if not iso: return False
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return d.date() == datetime.now(timezone.utc).date()
    except Exception:
        return False
def dest_of(product):
    return "bar" if (product.get("type") or "food") == "beverage" else "cucina"
def find_ticket(data, tid, dest):
    for o in data:
        if str(o.get("tableId"))==tid and o.get("destination")==dest and o.get("status") in ("inviato","in_preparazione"):
            return o
    return None
def add_item(tid, tname, product, qty=1):
    dest = dest_of(product)
    data = load_orders()
    if fix_stuck(data):
        save_orders(data); data = load_orders()
    target = find_ticket(data, tid, dest)
    item = {"qty": int(qty or 1), "name": product["name"], "type": product.get("type") or "food", "price": float(product["price"]), "variant": "", "productId": product["id"]}
    if target:
        target.setdefault("items", []).append(item)
        target["total"] = sum(float(i.get("price") or 0)*int(i.get("qty") or 1) for i in target["items"])
        target["status"] = "inviato"
    else:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        target = {"id": "ord_" + hex(int(time.time()*1000))[2:], "items": [item], "total": float(product["price"])*int(qty or 1), "paidAt": None, "status": "inviato", "readyAt": None, "tableId": tid, "servedAt": None, "createdAt": now, "tableName": tname, "destination": dest}
        data.append(target)
    save_orders(data)
    return target
def split_products(chunk):
    chunk = re.sub(r"\bal tavolo\b.*", "", chunk, flags=re.I)
    chunk = re.sub(r"\btavolo\s*\d+\b", "", chunk, flags=re.I)
    parts = re.split(r"\s+e\s+|,\s*", chunk)
    out = []
    for p in parts:
        p = re.sub(r"^(aggiungi|metti|manda|invia|apri)\s+", "", p.strip(), flags=re.I).strip(" .")
        if p: out.append(p)
    return out
def wants_finance(text):
    low = (text or "").lower()
    return any(k in low for k in ("report", "incass", "fatturat", "scontrin", "vendit", "quanto abbiamo", "quanto ho", "dashboard", "kpi"))
def wants_image(text):
    low = (text or "").lower()
    return any(k in low for k in ("genera immagine", "genera post", "post instagram", "immagine ig", "crea post", "visual post", "grok imagine", "genera visual"))
def ig_prompt_from(text):
    low = (text or "").lower()
    base = "Instagram square 1080x1080 post for Italian brand Mente Locale, dark cyan neon premium tech, readable bold Italian text, high contrast social ad. "
    if "caso" in low or "prima" in low:
        return base + "PRIMA/DOPO split paper chaos vs digital tablet. CASO STUDIO."
    if "demo" in low:
        return base + "Gestionale UI glow. CTA da 1.999 euro."
    if "meme" in low or "pain" in low:
        return base + "Local business pain meme, fridge +10 ASL."
    if "testimon" in low:
        return base + "5 star testimonial card Mente Locale."
    if "offerta" in low or "1999" in low:
        return base + "Offerta diretta pacchetto 1.999 euro Sito Gestionale Agenda HACCP."
    extra = re.sub(r"genera (immagine|post|visual)|post instagram|immagine ig|crea post", "", text, flags=re.I).strip()
    return base + (extra or "Sell 1999 euro package to local businesses.")
def xai_chat(messages, max_tokens=700):
    if not XAI_API_KEY:
        return None
    payload = json.dumps({"model": XAI_CHAT_MODEL, "messages": messages, "max_tokens": max_tokens, "stream": False}).encode()
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=payload,
        headers={"Authorization": "Bearer " + XAI_API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        err = e.read().decode() if hasattr(e, "read") else str(e)
        return "xAI chat errore: " + err[:200]
def generate_image(prompt):
    if not XAI_API_KEY:
        return {"ok": False, "error": "Manca XAI_API_KEY. Crea chiave su https://console.x.ai/ e mettila su Railway."}
    payload = json.dumps({"model": XAI_IMAGE_MODEL, "prompt": prompt[:2000], "n": 1}).encode()
    req = urllib.request.Request(
        "https://api.x.ai/v1/images/generations",
        data=payload,
        headers={"Authorization": "Bearer " + XAI_API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read().decode())
        url = None
        if isinstance(data.get("data"), list) and data["data"]:
            item = data["data"][0]
            url = item.get("url") or item.get("image_url")
            if not url and item.get("b64_json"):
                url = "data:image/png;base64," + item["b64_json"]
        return {"ok": bool(url), "url": url}
    except Exception as e:
        err = e.read().decode() if hasattr(e, "read") else str(e)
        return {"ok": False, "error": err[:400]}
def snapshot():
    try:
        orders = load_orders()
        today = [o for o in orders if same_day(o.get("createdAt")) or same_day(o.get("paidAt"))]
        paid = [o for o in today if o.get("status") == "pagato" or o.get("paidAt")]
        attesa = [o for o in orders if o.get("status") in ("inviato","in_preparazione","pronto")]
        tot = sum(float(o.get("total") or 0) for o in paid)
        return f"Incasso oggi {tot:.2f} euro, {len(paid)} scontrini. Comande aperte {len(attesa)}."
    except Exception:
        return "Gestionale non letto."
def build_backup():
    orders = load_orders()
    today = [o for o in orders if same_day(o.get("createdAt")) or same_day(o.get("paidAt"))]
    paid = [o for o in today if o.get("status") == "pagato" or o.get("paidAt")]
    attesa = [o for o in orders if o.get("status") in ("inviato","in_preparazione","pronto")]
    tot = sum(float(o.get("total") or 0) for o in paid)
    medio = (tot / len(paid)) if paid else 0.0
    riassunto = f"Report Teste Matte {datetime.now().strftime('%d/%m/%Y')}. Incasso {tot:.2f} euro. Scontrini {len(paid)}. Medio {medio:.2f}. Aperte {len(attesa)}."
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "brand": "Teste Matte", "incasso_oggi": round(tot, 2), "scontrini": len(paid), "scontrino_medio": round(medio, 2), "comande_aperte": len(attesa), "ordini_oggi": today, "tutti_ordini": orders, "riassunto_it": riassunto}
def send_whatsapp_text(text):
    if not WA_TOKEN or not WA_PHONE_ID:
        return {"ok": False, "error": "Mancano WHATSAPP_TOKEN e WHATSAPP_PHONE_ID"}
    url = f"https://graph.facebook.com/v18.0/{WA_PHONE_ID}/messages"
    payload = json.dumps({"messaging_product": "whatsapp", "to": WA_TO.replace("+", "").replace(" ", ""), "type": "text", "text": {"body": text[:4000]}}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Authorization": "Bearer " + WA_TOKEN, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"ok": True, "resp": json.loads(r.read().decode())}
    except Exception as e:
        err = e.read().decode() if hasattr(e, "read") else str(e)
        return {"ok": False, "error": err[:300]}
def cassiere(text):
    t = (text or "").strip(); low = t.lower()
    data = load_orders()
    if fix_stuck(data): save_orders(data)
    if "report" in low:
        return build_backup()["riassunto_it"] + "\n\nFile JSON: /api/backup"
    if wants_finance(low) or ("quanto" in low and "oggi" in low):
        orders = load_orders()
        today = [o for o in orders if same_day(o.get("createdAt")) or same_day(o.get("paidAt"))]
        paid = [o for o in today if o.get("status") == "pagato" or o.get("paidAt")]
        tot = sum(float(o.get("total") or 0) for o in paid)
        return f"Oggi {len(paid)} scontrini pagati, incasso {tot:.2f} euro."
    if low in ("tavoli", "elenco tavoli", "stato tavoli"):
        opened = [o for o in load_orders() if o.get("status") in ("inviato","in_preparazione","pronto")]
        if not opened: return "Nessun tavolo in attesa."
        return "In attesa: " + ", ".join(f"{o.get('tableName')} {o.get('destination')} {o.get('total')}e" for o in opened[:20])
    m_tav = re.search(r"(?:tavolo|t)\s*(\d+)|bancone|dehors\s*(\d+)", low)
    want_open = bool(re.search(r"\b(aggiungi tavolo|apri tavolo|apri t\s*\d+|tavolo\s*\d+)\b", low))
    want_add = bool(re.search(r"\b(aggiungi|metti|manda|invia)\b", low)) and bool(m_tav)
    tid = tname = None
    if m_tav: tid, tname = table_id(m_tav.group(0))
    if want_open and tid and not re.search(r"aggiungi .+\s+(al\s+)?tavolo", low):
        only_table = not re.search(r"aggiungi\s+(?!tavolo)([a-z].+)", low)
        if only_table or low.startswith("apri") or low.startswith("aggiungi tavolo"):
            return f"Tavolo {tname} pronto. Dimmi i prodotti."
    if want_add and tid:
        phrase = re.sub(r"aggiungi\s+tavolo\s+\d+,?\s*", "", t, flags=re.I)
        phrase = re.sub(r"\b(al\s+)?tavolo\s*\d+\b", "", phrase, flags=re.I)
        names = split_products(phrase)
        if not names: return f"Tavolo {tname} pronto. Dimmi i prodotti."
        found, missing = [], []
        for n in names:
            p = search_product(n)
            if p: found.append(p)
            else: missing.append(n)
        if missing: return "ERRORE: " + ", ".join(missing) + " non trovato nel gestionale."
        lines = []; dests = set(); tot = 0
        for p in found:
            ticket = add_item(tid, tname, p, 1)
            dests.add(ticket.get("destination"))
            tot += float(p["price"])
            lines.append(f"1x {p['name']} ({p['price']:.2f} euro)")
        return f"Inviato a {' e '.join(sorted(dests))}. Tavolo {tname}: " + ", ".join(lines) + f". Totale: {tot:.2f} euro"
    if want_open and tid: return f"Tavolo {tname} pronto. Dimmi i prodotti."
    return None
def llm(messages):
    if XAI_API_KEY:
        out = xai_chat(messages)
        if out and not str(out).startswith("xAI chat errore"):
            return out
    if groq:
        try:
            r = groq.chat.completions.create(model="openai/gpt-oss-20b", messages=messages, max_tokens=700)
            return r.choices[0].message.content or "Ricevuto."
        except Exception as e:
            return "Cervello Groq: " + str(e)[:120]
    return "Nessun cervello LLM configurato (XAI_API_KEY o GROQ_API_KEY)."
def pensa(text):
    c = cassiere(text)
    if c: return c, None
    if wants_image(text):
        prompt = ig_prompt_from(text)
        img = generate_image(prompt)
        if img.get("ok"):
            caption = "Post Instagram pronto.\nHook: ordine, non caos.\nCTA: Mente Locale da 1.999 euro.\nLink: https://mente-locale-premium.vercel.app/"
            return caption, img.get("url")
        return "Immagine non generata: " + str(img.get("error") or "errore"), None
    msgs = [{"role": "system", "content": SYS}]
    if wants_finance(text):
        msgs.append({"role": "user", "content": "[Gestionale]\n" + snapshot() + "\n\n[Richiesta]\n" + text})
    else:
        msgs.append({"role": "user", "content": text})
    return llm(msgs), None
def clean_voice(text):
    return re.sub(r"\s+", " ", str(text or ""))[:280]
@app.get("/health")
def health():
    return {"status": "ok", "agent": "Jarvis", "xai": bool(XAI_API_KEY), "groq": bool(GROQ_API_KEY), "chat_model": XAI_CHAT_MODEL if XAI_API_KEY else "groq", "image_model": XAI_IMAGE_MODEL if XAI_API_KEY else None}
@app.get("/")
def root():
    return FileResponse("index.html") if os.path.exists("index.html") else health()
@app.get("/report")
def report_page():
    if os.path.exists("report.html"): return FileResponse("report.html")
    return Response(content=b"report.html missing", status_code=500)
@app.get("/report.html")
def report_page_html():
    return report_page()
@app.get("/api/backup")
def api_backup():
    return JSONResponse(build_backup())
@app.post("/api/backup/whatsapp")
def api_backup_wa():
    b = build_backup()
    wa = send_whatsapp_text(b.get("riassunto_it", ""))
    return {"riassunto_it": b.get("riassunto_it"), "whatsapp": wa}
@app.post("/api/image")
def api_image(body: ImageIn):
    prompt = body.prompt.strip() or ig_prompt_from(body.theme or "post instagram")
    return generate_image(prompt)
@app.post("/api/speak")
def api_speak(body: SpeakIn):
    text = clean_voice(body.text)
    if not text: return Response(status_code=400)
    payload = json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE}", data=payload, headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return Response(content=r.read(), media_type="audio/mpeg")
    except Exception as e:
        return Response(content=str(e).encode(), status_code=502)
@app.get("/api/products/search")
def api_search(q: str = Query("")):
    return {"found": bool(search_product(q)), "q": q, "product": search_product(q)}
@app.get("/api/tables")
def api_tables():
    opened = [o for o in load_orders() if o.get("status") in ("inviato","in_preparazione","pronto")]
    return {"aperti": [{"id": o.get("tableId"), "name": o.get("tableName"), "dest": o.get("destination"), "status": o.get("status"), "total": o.get("total")} for o in opened]}
@app.post("/chat")
def chat(body: ChatIn):
    text = (body.message or "").strip()
    if not text: return {"risposta": "Dimmi pure, signore."}
    try:
        risposta, image_url = pensa(text)
        out = {"risposta": risposta}
        if image_url: out["image_url"] = image_url
        if "report" in text.lower():
            out["backup_url"] = "/api/backup"
            out["download"] = True
        return out
    except Exception as e:
        return {"risposta": "Errore: " + str(e)[:200]}
