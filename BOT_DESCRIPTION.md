# Come Configurare la Descrizione del Bot con Link Affiliate

## Link Base Affiliate

Il bot genera automaticamente un link base per la homepage Amazon con il tuo tag affiliate:
```
https://www.amazon.it/?tag=TUO_TAG_AFFILIATE
```

Questo link può essere usato nella descrizione del bot o nel messaggio di start.

## Come Aggiungere il Link nella Descrizione del Bot

### Passo 1: Genera il Link

Il link base viene generato automaticamente dal bot usando:
- **Regione**: Configurata in `AMAZON_REGION` (default: IT)
- **Tag Affiliate**: Configurato in `AMAZON_AFFILIATE_TAG`

Formato: `https://www.amazon.it/?tag=TUO_TAG_AFFILIATE`

### Passo 2: Configura tramite BotFather

1. Apri Telegram e vai a [@BotFather](https://t.me/BotFather)
2. Invia il comando `/mybots`
3. Seleziona il tuo bot
4. Clicca su "Edit Bot" → "Edit Description"
5. Aggiungi una descrizione come questa:

```
Bot per monitorare i prezzi Amazon! 

📦 Aggiungi prodotti alla watchlist
📉 Ricevi notifiche quando i prezzi scendono
🛍️ Acquista su Amazon: https://www.amazon.it/?tag=TUO_TAG_AFFILIATE

Comandi:
/start - Avvia il bot
/watchlist - Vedi i tuoi prodotti
```

### Passo 3: Aggiungi il Link anche nella Short Description

1. In BotFather, vai su "Edit Bot" → "Edit Short Description"
2. Aggiungi una versione breve:

```
Monitora prezzi Amazon e risparmia! 🛍️ https://www.amazon.it/?tag=TUO_TAG_AFFILIATE
```

## Come Funziona il Link Base

Il link `https://www.amazon.it/?tag=TUO_TAG_AFFILIATE`:
- Reindirizza alla homepage di Amazon
- Qualsiasi acquisto fatto entro 24 ore dal click genererà commissioni affiliate
- Funziona anche se l'utente naviga su Amazon e compra altri prodotti

## Link nel Messaggio di Start

Il bot include automaticamente il link base nel messaggio di `/start`, quindi gli utenti lo vedranno sempre quando iniziano a usare il bot.

## Esempio di Descrizione Completa

```
🛍️ Bot Monitor Prezzi Amazon

Monitora i prezzi dei prodotti Amazon e ricevi notifiche quando scendono!

✨ Funzionalità:
• Aggiungi prodotti alla watchlist
• Monitoraggio automatico prezzi
• Notifiche quando i prezzi scendono
• Link affiliate automatici

🛒 Acquista su Amazon: https://www.amazon.it/?tag=TUO_TAG_AFFILIATE

Comandi:
/start - Avvia il bot
/watchlist - Vedi i tuoi prodotti monitorati
/remove <asin> - Rimuovi un prodotto
```

## Note Importanti

⚠️ **Ricorda**:
- Sostituisci `TUO_TAG_AFFILIATE` con il tuo tag reale
- Il link deve essere valido e funzionante
- Verifica che il tag sia corretto prima di pubblicare
- Il link base funziona per tutti gli acquisti su Amazon, non solo per prodotti specifici

