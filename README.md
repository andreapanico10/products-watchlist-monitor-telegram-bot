# Amazon Affiliate Bot

Bot Telegram per monitorare i prezzi dei prodotti Amazon e ricevere notifiche quando il prezzo scende, con link affiliate automatici.

## Funzionalità

- Aggiungi prodotti Amazon alla watchlist inviando il link
- Monitoraggio automatico dei prezzi tramite Amazon PA-API
- Notifiche quando il prezzo scende sotto il prezzo iniziale o target
- Gestione watchlist: visualizza e rimuovi prodotti
- Link affiliate automatici nelle notifiche

## Setup

### Prerequisiti

- Python 3.9+
- PostgreSQL
- Account Amazon Associate con accesso a PA-API
- Bot Telegram (crea tramite @BotFather)

### Installazione

1. Clona il repository e installa le dipendenze:
```bash
pip install -r requirements.txt
```

2. Copia `env.example` in `.env` e configura le variabili:
```bash
cp env.example .env
```

3. Configura le variabili d'ambiente in `.env`:
   - `TELEGRAM_BOT_TOKEN`: Token del bot Telegram
   - `DATABASE_URL`: URL di connessione PostgreSQL
   - `AMAZON_ACCESS_KEY`: Access Key di Amazon PA-API
   - `AMAZON_SECRET_KEY`: Secret Key di Amazon PA-API
   - `AMAZON_ASSOCIATE_TAG`: Associate Tag Amazon
   - `AMAZON_AFFILIATE_TAG`: Codice affiliate per i link
   - `AMAZON_REGION`: Regione Amazon (IT, US, UK, etc.)
   - `PRICE_CHECK_INTERVAL_HOURS`: Frequenza controllo prezzi (default: 6)

4. Inizializza il database:
```bash
alembic upgrade head
```

5. Avvia il bot:
```bash
python main.py
```

## Utilizzo

- Invia un link Amazon al bot per aggiungere un prodotto alla watchlist
- Usa `/watchlist` per vedere i tuoi prodotti monitorati
- Usa `/remove <asin>` per rimuovere un prodotto dalla watchlist
- Riceverai notifiche automatiche quando il prezzo scende

## Note

- Amazon PA-API ha limiti di rate limiting (1 richiesta/secondo per account gratuito)
- Il bot controlla i prezzi periodicamente secondo l'intervallo configurato
- I link affiliate vengono generati automaticamente quando il prezzo scende

