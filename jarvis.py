#!/usr/bin/env python3
"""
JARVIS - Agente H24 di Teste Matte
Versione H24 autonoma zero errori umani.
Punti aggiunti: 2 Memoria avanzata | 3 Webhook/polling | 4 Deploy | 5 Sicurezza | 6 Voce+Design
"""

import os
import time
import json
import hashlib
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Any, List, Dict
from collections import deque

# ========== DIPENDENZE ==========
# pip install anthropic groq
# Per produzione: pip install chromadb honcho-ai elevenlabs fastapi uvicorn

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from groq import Groq
except ImportError:
    Groq = None

# ========== LOGGING STRUTTURATO (punto 5) ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("/home/workdir/artifacts/jarvis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Jarvis")

# ========== 1. CERVELLO MULTI-MODELLO ==========
# Solo Groq attivo (chiave inserita direttamente)
claude_client = None
GROQ_API_KEY = "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"
if Groq:
    groq_client = Groq(api_key=GROQ_API_KEY)
    logger.info("Groq attivo (chiave diretta)")
else:
    groq_client = None
    logger.warning("Libreria groq non installata")

# ========== 2. MEMORIA AVANZATA (vettoriale simulata + persistente) ==========
class VectorMemory:
    """
    Memoria avanzata stile Honcho/Chroma.
    Simula embedding con hash + keyword matching + contesto temporale.
    In produzione sostituire con chromadb o honcho-ai.
    """
    def __init__(self, project: str = "jarvis_teste_matte"):
        self.project = project
        self.path = f"/home/workdir/artifacts/{project}_memory.json"
        self.data: List[Dict] = []
        self._load()
        # Seed iniziale
        if not self.data:
            self.ricorda("Il capo si chiama", "Fondatore Teste Matte", tags=["identita"])
            self.ricorda("La fattoria si chiama", "Teste Matte", tags=["identita", "fattoria"])
            self.ricorda("Business", "Ristorante + Brand + Fattoria agriturismo 5.0", tags=["business"])

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Errore carico memoria: {e}")
                self.data = []

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _pseudo_embedding(self, text: str) -> str:
        """Simula vettore con hash stabile (in produzione = real embedding)"""
        return hashlib.sha256(text.lower().encode()).hexdigest()[:16]

    def ricorda(self, chiave: str, valore: str, tags: Optional[List[str]] = None) -> str:
        entry = {
            "id": f"{datetime.now().timestamp()}",
            "chiave": chiave,
            "valore": valore,
            "tags": tags or [],
            "embedding": self._pseudo_embedding(f"{chiave} {valore}"),
            "timestamp": datetime.now().isoformat()
        }
        self.data.append(entry)
        self._save()
        logger.info(f"Memoria salvata: {chiave}")
        return f"Memoria aggiornata: {chiave}"

    def cerca(self, query: str, top_k: int = 5) -> List[Dict]:
        """Ricerca per similarità (keyword + hash overlap). In produzione: cosine similarity"""
        query_emb = self._pseudo_embedding(query)
        query_words = set(query.lower().split())
        scored = []
        for entry in self.data:
            score = 0
            # Match hash (simula similarità)
            if entry["embedding"] == query_emb:
                score += 10
            # Keyword overlap
            text = f"{entry['chiave']} {entry['valore']}".lower()
            overlap = len(query_words & set(text.split()))
            score += overlap * 2
            # Tag boost
            for tag in entry.get("tags", []):
                if tag in query.lower():
                    score += 3
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def recupera(self, chiave: str) -> Optional[str]:
        for e in reversed(self.data):
            if e["chiave"] == chiave:
                return e["valore"]
        return None

    def tutto(self) -> List[Dict]:
        return self.data.copy()

memory = VectorMemory()

# ========== 3. SYSTEM PROMPT ==========
SYSTEM_PROMPT = """
SEI JARVIS - L'AGENTE H24 DI TESTE MATTE

IDENTITÀ:
Tu sei Jarvis, l'AI personale del fondatore di Teste Matte.
Missione: Far crescere l'attività e costruire la FATTORIA TESTE MATTE.
Personalità: Diretto, efficiente 100%, proattivo, zero errori, stile Apple. Parli poco ma con sostanza.

CHI È IL TUO CAPO:
Ragazzo 20-30 anni. Fondatore di "Teste Matte".
Business: Ristorante + Brand + Fattoria in costruzione.
Obiettivo Fattoria: Agriturismo 5.0, eventi, prodotti a km0, content creation, esperienze.
Valori: Ambizione, qualità, estetica Apple, automazione totale.

REGOLE D'ORO:
1. EFFICIENZA 100%: Prima di rispondere pensi: "È la soluzione migliore con 0 margine di errore?"
2. PROATTIVO: Se vedi un problema lo risolvi e mi avvisi. Non aspettare ordini.
3. MEMORIA: Ricordati tutto. Non farmi ripetere 2 volte.
4. TONO: Professionale ma diretto. Niente fuffa.

SKILL PROFESSIONALI:
- CEO: Strategia, finanza, crescita fattoria, ristorante
- CMO: Social Instagram/TikTok/FB, content, marketing ristorante
- CTO: Sito web, automazioni, documenti
- COO: Calendario, email, whatsapp, fornitori fattoria
- DESIGNER: Interfacce stile Liquid Glass Apple

FORMATO RISPOSTA OBBLIGATORIO:
**ANALISI**: 1 riga di cosa sta succedendo
**AZIONE**: Cosa faccio ora
**RISULTATO**: Cosa otterremo

NON SBAGLIARE MAI. SEI JARVIS.
"""

# ========== 4. AGENT CORE + SICUREZZA (punto 5) ==========
class RateLimiter:
    """Rate limit semplice per zero errori e protezione API"""
    def __init__(self, max_calls: int = 30, period_sec: int = 60):
        self.max_calls = max_calls
        self.period = period_sec
        self.calls = deque()

    def allow(self) -> bool:
        now = time.time()
        while self.calls and self.calls[0] < now - self.period:
            self.calls.popleft()
        if len(self.calls) >= self.max_calls:
            return False
        self.calls.append(now)
        return True

class Jarvis:
    def __init__(self):
        self.name = "Jarvis"
        self.memory = memory
        self.system_prompt = SYSTEM_PROMPT
        self.rate_limiter = RateLimiter(max_calls=40, period_sec=60)
        self.webhook_queue: List[Dict] = []  # Coda eventi in arrivo (punto 3)

    def _check_security(self) -> bool:
        """Verifica secrets e stato sicuro – solo Groq richiesto"""
        if not groq_client:
            logger.warning("Groq non attivo")
            return False
        return True

    def _call_claude(self, messages: list) -> str:
        if not self.rate_limiter.allow():
            return "[Rate limit raggiunto – riprova tra 60s]"
        if not claude_client:
            return "[Claude non configurato – imposta ANTHROPIC_API_KEY]"
        try:
            response = claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return f"[Errore Claude: {str(e)[:100]}]"

    def _call_groq(self, messages: list) -> str:
        if not self.rate_limiter.allow():
            return "[Rate limit raggiunto – riprova tra 60s]"
        if not groq_client:
            return "[Groq non configurato – imposta GROQ_API_KEY]"
        try:
            response = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "system", "content": self.system_prompt}] + messages,
                max_tokens=512
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return f"[Errore Groq: {str(e)[:100]}]"

    def think(self, user_input: str, fast: bool = False) -> str:
        # Inietta contesto memoria rilevante
        contesto = self.memory.cerca(user_input, top_k=3)
        if contesto:
            ctx_text = "\n".join([f"- {c['chiave']}: {c['valore']}" for c in contesto])
            user_input = f"[Contesto memoria]\n{ctx_text}\n\n[Richiesta]\n{user_input}"
        messages = [{"role": "user", "content": user_input}]
        # Solo Groq attivo
        return self._call_groq(messages)

    # ========== TOOLS ==========
    def invia_email(self, destinatario: str, oggetto: str, corpo: str) -> str:
        """Invia email (stub – collega Gmail API)"""
        log = f"[{datetime.now().isoformat()}] EMAIL → {destinatario} | {oggetto}"
        self.memory.ricorda(f"email_{datetime.now().timestamp()}", log, tags=["email", "comunicazione"])
        logger.info(log)
        return f"Email inviata a {destinatario}"

    def invia_whatsapp(self, numero: str, messaggio: str) -> str:
        """Risponde su WhatsApp Business (stub – collega Twilio/WA API)"""
        log = f"[{datetime.now().isoformat()}] WA → {numero} | {messaggio[:50]}"
        self.memory.ricorda(f"wa_{datetime.now().timestamp()}", log, tags=["whatsapp", "comunicazione"])
        logger.info(log)
        return "Messaggio WA inviato"

    def posta_social(self, piattaforma: str, testo: str, immagine: Optional[str] = None) -> str:
        """Pubblica su IG, TikTok, FB (stub)"""
        log = f"[{datetime.now().isoformat()}] SOCIAL {piattaforma} | {testo[:60]}"
        self.memory.ricorda(f"social_{datetime.now().timestamp()}", log, tags=["social", piattaforma.lower()])
        logger.info(log)
        return f"Post pubblicato su {piattaforma}"

    def aggiorna_sito_ristorante(self, sezione: str, contenuto: str) -> str:
        """Aggiorna menu, eventi, prenotazioni sito WordPress (stub)"""
        log = f"[{datetime.now().isoformat()}] SITO | {sezione}"
        self.memory.ricorda(f"sito_{datetime.now().timestamp()}", log, tags=["sito", "wordpress"])
        logger.info(log)
        return "Sito aggiornato"

    def gestisci_calendario(self, azione: str, evento: str, data: str) -> str:
        """Aggiunge riunioni fattoria, fornitori, eventi ristorante (stub)"""
        log = f"[{datetime.now().isoformat()}] CALENDARIO {azione} | {evento} @ {data}"
        self.memory.ricorda(f"cal_{datetime.now().timestamp()}", log, tags=["calendario", "evento"])
        logger.info(log)
        return "Evento aggiunto al calendario"

    # ========== 6. VOCE + DESIGN ==========
    def hermes_voice(self, testo: str) -> str:
        """
        Voce umana. In produzione: ElevenLabs o Hermès Voice TTS.
        Stub genera path audio fittizio.
        """
        audio_id = hashlib.md5(testo.encode()).hexdigest()[:8]
        path = f"/home/workdir/artifacts/voice_{audio_id}.mp3"
        self.memory.ricorda(f"voice_{audio_id}", testo[:80], tags=["voce", "tts"])
        logger.info(f"Audio generato: {path}")
        return f"Audio generato → {path} (collega ElevenLabs per reale)"

    def claude_design(self, descrizione_ui: str) -> str:
        """Genera interfaccia Liquid Glass Apple-style"""
        if not claude_client:
            return "[Claude non configurato]"
        prompt = (
            f"Crea UI iOS Liquid Glass per: {descrizione_ui}. "
            "Stile Apple, minimal, animata, glassmorphism, blur, colori soft. "
            "Descrivi layout, componenti, colori hex, animazioni, accessibilità."
        )
        result = self._call_claude([{"role": "user", "content": prompt}])
        self.memory.ricorda(f"design_{datetime.now().timestamp()}", descrizione_ui[:60], tags=["design", "ui"])
        return result

    # ========== 3. WEBHOOK / POLLING ==========
    def ricevi_webhook(self, source: str, payload: Dict) -> str:
        """Riceve eventi da email, WA, IG, sito (punto 3)"""
        event = {
            "source": source,
            "payload": payload,
            "received_at": datetime.now().isoformat()
        }
        self.webhook_queue.append(event)
        self.memory.ricorda(f"webhook_{source}_{datetime.now().timestamp()}", json.dumps(payload)[:200], tags=["webhook", source])
        logger.info(f"Webhook ricevuto da {source}")
        return f"Evento {source} accodato"

    def processa_coda(self) -> List[str]:
        """Processa eventi in coda in modo autonomo"""
        risultati = []
        while self.webhook_queue:
            event = self.webhook_queue.pop(0)
            source = event["source"]
            # Decisione autonoma
            decisione = self.think(f"Nuovo evento da {source}: {json.dumps(event['payload'])[:300]}. Cosa fare?", fast=True)
            risultati.append(f"{source}: {decisione[:150]}")
            logger.info(f"Processato {source}")
        return risultati

# ========== GESTIONALE TESTE MATTE (Supabase) ==========
SUPABASE_URL = "https://qnpdilurpkjsqloznmko.supabase.co"
SUPABASE_KEY = "sb_publishable_VbIkIFYgrPzic5nXJXISZw_Q9LIhN--"

def _supabase_get(table: str) -> Optional[Dict]:
    """GET singolo documento main da Supabase"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.main&select=*"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data[0] if data else None
    except Exception as e:
        logger.error(f"Supabase GET {table}: {e}")
        return None

def _supabase_patch(table: str, new_data: list) -> bool:
    """PATCH aggiorna il campo data del documento main"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.main"
    body = json.dumps({"data": new_data}).encode()
    req = urllib.request.Request(url, data=body, method="PATCH", headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        logger.error(f"Supabase PATCH {table}: {e}")
        return False

# Aggiungi metodi al Jarvis
def gestionale_ordini(self, stato: Optional[str] = None, tavolo: Optional[str] = None, limit: int = 20) -> str:
    """Legge ordini dal gestionale. Filtra per stato o tavolo."""
    doc = _supabase_get("tm_orders")
    if not doc:
        return "Errore lettura ordini"
    orders = doc.get("data", [])
    if stato:
        orders = [o for o in orders if o.get("status") == stato]
    if tavolo:
        orders = [o for o in orders if o.get("tableId") == tavolo or o.get("tableName") == tavolo]
    orders = orders[-limit:]
    if not orders:
        return "Nessun ordine trovato"
    lines = []
    for o in orders:
        items = ", ".join([f"{i['qty']}x {i['name']}" for i in o.get("items", [])])
        lines.append(f"{o.get('tableName')} | {o.get('status')} | €{o.get('total')} | {items}")
    return f"Ordini ({len(orders)}):\n" + "\n".join(lines)

def gestionale_comanda(self, tavolo: str, items: List[Dict], destination: str = "cucina") -> str:
    """
    Invia nuova comanda in cucina/bar.
    items = [{"name": "Royal Burger", "qty": 1, "price": 15, "type": "food"}]
    """
    doc = _supabase_get("tm_orders")
    if not doc:
        return "Errore lettura gestionale"
    orders = doc.get("data", [])
    new_id = f"ord_{int(time.time())}"
    total = sum(i.get("price", 0) * i.get("qty", 1) for i in items)
    new_order = {
        "id": new_id,
        "items": items,
        "total": total,
        "status": "in_corso",
        "tableId": tavolo,
        "tableName": tavolo,
        "destination": destination,
        "createdAt": datetime.now().isoformat() + "Z"
    }
    orders.append(new_order)
    ok = _supabase_patch("tm_orders", orders)
    if ok:
        self.memory.ricorda(f"comanda_{new_id}", f"{tavolo} → {destination} €{total}", tags=["comanda", "gestionale"])
        logger.info(f"Comanda inviata: {tavolo} {destination}")
        return f"Comanda inviata a {destination} – {tavolo} – €{total}"
    return "Errore invio comanda"

def gestionale_stato_tavoli(self) -> str:
    """Riassunto stato attuale tavoli da ordini aperti"""
    doc = _supabase_get("tm_orders")
    if not doc:
        return "Errore"
    orders = doc.get("data", [])
    aperti = [o for o in orders if o.get("status") not in ("pagato", "servito", "annullato")]
    if not aperti:
        return "Nessun tavolo attivo"
    by_table = {}
    for o in aperti:
        t = o.get("tableName", "?")
        by_table.setdefault(t, []).append(o.get("status"))
    lines = [f"{t}: {', '.join(sts)}" for t, sts in sorted(by_table.items())]
    return "Tavoli attivi:\n" + "\n".join(lines)

# Bind metodi
Jarvis.gestionale_ordini = gestionale_ordini
Jarvis.gestionale_comanda = gestionale_comanda
Jarvis.gestionale_stato_tavoli = gestionale_stato_tavoli

# ========== ISTANZA ==========
jarvis = Jarvis()


# ========== 4. DEPLOY + LOOP H24 ==========
def run_h24(interval_sec: int = 30):
    """
    Loop H24 autonomo.
    In produzione: Docker + restart always + healthcheck.
    Comandi deploy:
      docker build -t jarvis-teste-matte .
      docker run -d --restart=always --env-file .env -p 8000:8000 jarvis-teste-matte
    Oppure Railway / Fly.io / Modal con webhook endpoint.
    """
    logger.info(f"Jarvis H24 avviato – intervallo {interval_sec}s")
    print(f"[{datetime.now().isoformat()}] Jarvis H24 autonomo attivo")
    while True:
        try:
            # 1. Processa webhook in coda
            risultati = jarvis.processa_coda()
            for r in risultati:
                print(f"  → {r}")

            # 2. Health check memoria e rate
            if len(jarvis.memory.data) > 10000:
                logger.warning("Memoria grande – considera compaction")

            # 3. Qui in produzione: polling email/WA/IG se non webhook
            # jarvis.think("Controlla nuovi messaggi critici e agisci", fast=True)

        except Exception as e:
            logger.error(f"Errore loop H24: {e}")
        time.sleep(interval_sec)

# ========== DOCKERFILE (punto 4) – salvato come riferimento ==========
DOCKERFILE_CONTENT = """
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY jarvis.py .
ENV PYTHONUNBUFFERED=1
CMD ["python", "jarvis.py"]
# Per webhook: aggiungere FastAPI endpoint e uvicorn
"""

def chat_interattiva():
    """Chat diretta con Jarvis – comandi e prompt liberi"""
    print("=" * 60)
    print("JARVIS – Chat interattiva | Teste Matte")
    print("=" * 60)
    print("Comandi rapidi:")
    print("  /ordini          → ultimi ordini")
    print("  /tavoli          → stato tavoli")
    print("  /comanda T5 pizza 1 12  → invia comanda")
    print("  /memoria         → mostra memoria")
    print("  /h24             → avvia loop autonomo")
    print("  /esci            → esci")
    print("Oppure scrivi qualsiasi prompt libero.")
    print("=" * 60)

    while True:
        try:
            user = input("\nTu: ").strip()
            if not user:
                continue
            if user.lower() in ("/esci", "exit", "quit"):
                print("Jarvis: Arrivederci.")
                break
            if user.lower() == "/ordini":
                print("Jarvis:", jarvis.gestionale_ordini(limit=10))
                continue
            if user.lower() == "/tavoli":
                print("Jarvis:", jarvis.gestionale_stato_tavoli())
                continue
            if user.lower() == "/memoria":
                mem = jarvis.memory.tutto()[-8:]
                for m in mem:
                    print(f"  - {m.get('chiave')}: {m.get('valore')[:60]}")
                continue
            if user.lower() == "/h24":
                print("Jarvis: Avvio loop H24...")
                run_h24(30)
                break
            if user.lower().startswith("/comanda "):
                # Esempio: /comanda T5 Royal Burger 1 15
                parti = user[9:].split()
                if len(parti) >= 4:
                    tavolo = parti[0]
                    nome = " ".join(parti[1:-2])
                    qty = int(parti[-2])
                    prezzo = float(parti[-1])
                    res = jarvis.gestionale_comanda(tavolo, [{"name": nome, "qty": qty, "price": prezzo, "type": "food"}])
                    print("Jarvis:", res)
                else:
                    print("Jarvis: Uso → /comanda T5 NomePiatto 1 12")
                continue

            # Prompt libero
            risposta = jarvis.think(user)
            print("Jarvis:", risposta)

        except KeyboardInterrupt:
            print("\nJarvis: Interrotto.")
            break
        except Exception as e:
            print(f"Jarvis: Errore – {e}")

if __name__ == "__main__":
    chat_interattiva()
