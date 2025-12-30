# Amazon Affiliate Bot

Bot Telegram per monitorare i prezzi dei prodotti Amazon e ricevere notifiche quando il prezzo scende, con link affiliate automatici.

## Funzionalità

- Aggiungi prodotti Amazon alla watchlist inviando il link
- Monitoraggio automatico dei prezzi tramite Amazon PA-API (opzionale)
- Notifiche quando il prezzo scende sotto il prezzo iniziale o target
- Gestione watchlist: visualizza e rimuovi prodotti
- Link affiliate automatici nelle notifiche
- Riepilogo giornaliero quando PA-API non è disponibile

## Setup con Docker (Consigliato)

### Prerequisiti

- Docker e Docker Compose installati
- Bot Telegram (crea tramite @BotFather)
- Account Amazon Associates (opzionale, per PA-API)

### Installazione Rapida

1. **Clona il repository e configura le variabili**:
```bash
cp env.example .env
```

2. **Modifica il file `.env`** con le tue credenziali:
```bash
TELEGRAM_BOT_TOKEN=il_tuo_token_qui
AMAZON_AFFILIATE_TAG=il_tuo_tag_affiliate
# ... altre configurazioni
```

3. **Avvia tutto con Docker Compose**:
```bash
docker-compose up -d
```

4. **Verifica i log**:
```bash
docker-compose logs -f bot
```

5. **Per fermare**:
```bash
docker-compose down
```

### Comandi Utili

```bash
# Avvia in background
docker-compose up -d

# Vedi i log
docker-compose logs -f bot

# Ferma i container
docker-compose down

# Ferma e rimuovi i volumi (cancella il database)
docker-compose down -v

# Riavvia solo il bot
docker-compose restart bot

# Riavvia tutto
docker-compose restart
```

## Setup Manuale (Senza Docker)

Vedi [SETUP.md](SETUP.md) per istruzioni dettagliate.

## Utilizzo

- Invia un link Amazon al bot per aggiungere un prodotto alla watchlist
- Usa `/watchlist` per vedere i tuoi prodotti monitorati
- Usa `/remove <asin>` per rimuovere un prodotto dalla watchlist
- Riceverai notifiche automatiche quando il prezzo scende (se PA-API è abilitata)
- Riceverai un riepilogo giornaliero con tutti i prodotti (se PA-API è disabilitata)

## Configurazione

### Modalità senza PA-API (Default)

```env
ENABLE_PA_API=false
DAILY_SUMMARY_HOUR=9
DAILY_SUMMARY_MINUTE=0
```

Il bot invierà un riepilogo giornaliero con tutti i prodotti nella watchlist.

### Modalità con PA-API

```env
ENABLE_PA_API=true
AMAZON_ACCESS_KEY=...
AMAZON_SECRET_KEY=...
AMAZON_ASSOCIATE_TAG=...
PRICE_CHECK_INTERVAL_HOURS=6
```

Il bot monitorerà i prezzi e invierà notifiche quando scendono.

## Note

- **Amazon PA-API**: Richiede 10 vendite qualificate negli ultimi 30 giorni
- **Rate Limiting**: Amazon limita a 1 richiesta/secondo per account gratuito
- **Database**: I dati sono persistenti nel volume Docker `postgres_data`
- **Backup**: Esegui backup del volume se necessario: `docker run --rm -v amazon-affiliate-bot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data`
