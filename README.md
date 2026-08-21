# Jarvis – Teste Matte

Agente H24 per ristorante + fattoria Teste Matte.

## Funzionalità
- Chat interattiva + comandi
- Collegamento gestionale Supabase (ordini, comande, tavoli)
- Memoria persistente
- Solo Groq (veloce)

## Comandi chat
- `/ordini` – ultimi ordini
- `/tavoli` – stato tavoli
- `/comanda T5 NomePiatto 1 15` – invia comanda
- `/memoria` – mostra memoria
- `/h24` – avvia loop autonomo
- oppure prompt libero

## Deploy Railway
1. Carica questi file su GitHub
2. Railway → New Project → Deploy from GitHub
3. Avvia

## Locale
```bash
pip install -r requirements.txt
python jarvis.py
```
