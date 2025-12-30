# Guida all'Avvio del Bot

## Passo 1: Installare le Dipendenze

```bash
# Assicurati di essere nella directory del progetto
cd /Users/andrea/Documents/Work/amazon-affiliate-bot

# Crea un ambiente virtuale (consigliato)
python3 -m venv venv

# Attiva l'ambiente virtuale
source venv/bin/activate  # Su macOS/Linux
# oppure
# venv\Scripts\activate  # Su Windows

# Installa le dipendenze
pip install -r requirements.txt
```

## Passo 2: Configurare PostgreSQL

Assicurati che PostgreSQL sia installato e in esecuzione:

```bash
# Verifica che PostgreSQL sia attivo
psql --version

# Crea il database (se non esiste)
createdb amazon_affiliate_bot

# Oppure usa psql:
psql -U postgres
CREATE DATABASE amazon_affiliate_bot;
\q
```

## Passo 3: Configurare Account Amazon per PA-API

Per utilizzare il bot, devi avere un account Amazon Associates con accesso a Product Advertising API (PA-API). Ecco come configurarlo:

### 3.1: Registrarsi come Amazon Associate

1. **Vai su Amazon Associates**:
   - Per l'Italia: https://affiliate-program.amazon.it/
   - Per altri paesi: cerca "Amazon Associates" nel tuo paese

2. **Crea un account** (se non ce l'hai già):
   - Clicca su "Iscriviti ora" o "Join Now"
   - Completa la registrazione con i tuoi dati
   - Accetta i termini e condizioni
   - Verifica la tua email

3. **Completa il profilo**:
   - Inserisci le informazioni richieste (sito web, metodo di pagamento, ecc.)
   - Attendi l'approvazione del tuo account (può richiedere 1-3 giorni)

### 3.2: Richiedere Accesso a PA-API

**⚠️ IMPORTANTE - Requisiti per PA-API:**

Amazon richiede i seguenti requisiti per accedere a Product Advertising API:

1. ✅ **Account di affiliazione approvato** - Il tuo account Amazon Associates deve essere attivo e approvato
2. ✅ **Conformità all'accordo operativo** - Devi rispettare i termini del programma di affiliazione
3. ✅ **10 vendite qualificate negli ultimi 30 giorni** - **Questo è il requisito più importante!**

**Se non hai ancora 10 vendite qualificate:**
- Non puoi accedere a PA-API finché non raggiungi questo obiettivo
- Devi generare almeno 10 vendite qualificate attraverso i tuoi link affiliate
- Una volta raggiunte le 10 vendite, l'accesso a PA-API diventerà disponibile automaticamente

**Come procedere:**

1. **Accedi a Amazon Associates Central**:
   - Vai su https://affiliate-program.amazon.it/home (o il sito del tuo paese)
   - Accedi con le tue credenziali

2. **Genera vendite qualificate**:
   - Usa SiteStripe o crea link affiliate manualmente
   - Condividi i link su siti web, social media, blog, ecc.
   - Attendi di raggiungere 10 vendite qualificate negli ultimi 30 giorni

3. **Una volta raggiunte le 10 vendite**:
   - Vai alla sezione "Tools" o "Strumenti" nel menu
   - Seleziona "Product Advertising API" o "PA-API"
   - L'accesso dovrebbe essere automaticamente disponibile
   - Clicca su "Create Credentials" o "Crea Credenziali" per ottenere le chiavi API

**Alternativa: SiteStripe**
- Amazon suggerisce di usare SiteStripe come alternativa temporanea
- SiteStripe permette di creare link affiliate manualmente, ma non è adatto per automazione
- Non può essere usato per il bot (richiede interazione manuale)

### 3.3: Ottenere le Credenziali PA-API

**⚠️ Solo dopo aver raggiunto 10 vendite qualificate negli ultimi 30 giorni:**

Una volta che hai raggiunto i requisiti e l'accesso è disponibile:

1. **Vai alla sezione Credentials**:
   - In Amazon Associates Central, vai su "Tools" > "Product Advertising API"
   - Cerca la sezione "Credentials" o "Credenziali"

2. **Crea o visualizza le credenziali**:
   - Se non hai ancora credenziali, clicca su "Create Credentials" o "Crea Credenziali"
   - Se le hai già, visualizza quelle esistenti

3. **Copia le seguenti informazioni**:
   - **Access Key (Access Key ID)**: Chiave di accesso pubblica
   - **Secret Key (Secret Access Key)**: Chiave segreta (mostrata solo una volta, salvala!)
   - **Associate Tag**: Il tuo tag associato (es: `tuonome-21` per Amazon.it)

4. **Nota importante**:
   - La Secret Key viene mostrata **solo una volta** al momento della creazione
   - Se la perdi, dovrai crearne una nuova
   - Salva queste credenziali in un posto sicuro

### 3.4: Ottenere il Codice Affiliate

Il codice affiliate (tag) è lo stesso dell'Associate Tag, ma puoi anche:

1. **Verificare il tuo Associate Tag**:
   - In Amazon Associates Central, vai su "Account Settings" > "Account Info"
   - Il tuo Associate Tag sarà qualcosa come `tuonome-21` (per Amazon.it)

2. **Usare lo stesso tag per i link**:
   - `AMAZON_AFFILIATE_TAG` può essere lo stesso di `AMAZON_ASSOCIATE_TAG`
   - Oppure puoi usare un tag diverso se ne hai più di uno

### 3.5: Limitazioni e Note

- **Requisiti per PA-API**:
  - ⚠️ **10 vendite qualificate negli ultimi 30 giorni** (requisito obbligatorio)
  - Account di affiliazione approvato e attivo
  - Conformità all'accordo operativo del programma
  
- **Rate Limiting**: 
  - Account gratuito: 1 richiesta/secondo
  - Il rate limiting aumenta automaticamente in base alle performance (vendite generate)
  
- **Regioni supportate**:
  - IT (Italia), US, UK, DE, FR, ES, CA, JP, AU
  - Assicurati di usare la regione corretta nel file `.env`

- **Mantenimento account**:
  - Devi avere almeno 3 vendite qualificate nei primi 180 giorni per mantenere l'account attivo
  - L'accesso a PA-API può essere revocato se non mantieni i requisiti o non rispetti i termini di servizio
  - Se le vendite scendono sotto le 10 negli ultimi 30 giorni, l'accesso a PA-API può essere sospeso

## Passo 4: Configurare le Variabili d'Ambiente

1. Copia il file di esempio:
```bash
cp env.example .env
```

2. Modifica il file `.env` con le tue credenziali:

```bash
# Telegram Bot Token (ottieni da @BotFather su Telegram)
TELEGRAM_BOT_TOKEN=il_tuo_token_qui

# Database (modifica user, password, host se necessario)
DATABASE_URL=postgresql://user:password@localhost:5432/amazon_affiliate_bot

# Amazon PA-API (ottieni da Amazon Associates Central - vedi Passo 3)
AMAZON_ACCESS_KEY=la_tua_access_key_qui
AMAZON_SECRET_KEY=la_tua_secret_key_qui
AMAZON_ASSOCIATE_TAG=il_tuo_associate_tag_qui
AMAZON_REGION=IT  # IT, US, UK, DE, FR, ES, CA, JP, AU

# Codice Affiliate (può essere lo stesso di AMAZON_ASSOCIATE_TAG)
AMAZON_AFFILIATE_TAG=il_tuo_tag_affiliate_qui

# Frequenza controllo prezzi (in ore)
PRICE_CHECK_INTERVAL_HOURS=6
```

**Esempio di configurazione completa**:
```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/amazon_affiliate_bot
AMAZON_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AMAZON_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AMAZON_ASSOCIATE_TAG=mionome-21
AMAZON_REGION=IT
AMAZON_AFFILIATE_TAG=mionome-21
PRICE_CHECK_INTERVAL_HOURS=6
```

## Passo 5: Inizializzare il Database

```bash
# Crea le tabelle usando Alembic
alembic upgrade head
```

Se Alembic non trova migrazioni, puoi creare le tabelle direttamente:

```bash
python3 -c "from database.database import engine, Base; from database.models import *; Base.metadata.create_all(bind=engine)"
```

## Passo 6: Avviare il Bot

```bash
python main.py
```

Il bot dovrebbe avviarsi e mostrare messaggi di log. Dovresti vedere:
- "Starting Amazon Affiliate Bot..."
- "Scheduler started"
- "Bot is running. Press Ctrl+C to stop."

## Test del Bot

1. Apri Telegram e cerca il tuo bot (usando il nome che hai dato a @BotFather)
2. Invia `/start` per vedere il messaggio di benvenuto
3. Invia un link Amazon per aggiungere un prodotto alla watchlist
4. Usa `/watchlist` per vedere i prodotti monitorati

## Risoluzione Problemi

### Errore: "TELEGRAM_BOT_TOKEN not set"
- Verifica che il file `.env` esista e contenga `TELEGRAM_BOT_TOKEN`

### Errore: "Could not connect to database"
- Verifica che PostgreSQL sia in esecuzione: `pg_isready`
- Controlla che `DATABASE_URL` nel `.env` sia corretto
- Verifica username e password

### Errore: "Amazon API credentials not configured"
- Assicurati di aver configurato `AMAZON_ACCESS_KEY`, `AMAZON_SECRET_KEY`, e `AMAZON_ASSOCIATE_TAG` nel file `.env`
- Verifica di aver completato il Passo 3 (Configurare Account Amazon per PA-API)
- Controlla che l'accesso a PA-API sia stato approvato da Amazon
- Verifica che le credenziali siano corrette e non scadute
- Assicurati che `AMAZON_REGION` corrisponda alla regione del tuo account Associates

### Errore: "No module named 'telegram'"
- Assicurati di aver attivato l'ambiente virtuale
- Reinstalla le dipendenze: `pip install -r requirements.txt`

## Note Importanti

- **Amazon PA-API**: 
  - Richiede registrazione come Amazon Associate e richiesta di accesso alle API (vedi Passo 3)
  - L'approvazione può richiedere 24-48 ore
  - Devi avere almeno 3 vendite qualificate nei primi 180 giorni per mantenere l'account attivo
  
- **Rate Limiting**: 
  - Account gratuito: 1 richiesta/secondo
  - Il bot gestisce automaticamente il rate limiting
  
- **Database**: 
  - Il bot crea automaticamente le tabelle se non esistono, ma è meglio usare Alembic per le migrazioni
  
- **Sicurezza**:
  - Non condividere mai le tue credenziali Amazon PA-API
  - Non committare il file `.env` su Git (è già nel `.gitignore`)
  - Mantieni le credenziali segrete e sicure


