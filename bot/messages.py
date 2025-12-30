"""Message templates for the Telegram bot."""
from typing import List, Dict


def get_welcome_message() -> str:
    """Get welcome message for /start command."""
    return """👋 Benvenuto nel Bot Monitor Prezzi Amazon!

📦 **Come funziona:**
1. Invia un link Amazon per aggiungere un prodotto alla watchlist
2. Il bot monitorerà automaticamente il prezzo
3. Riceverai una notifica quando il prezzo scende!

🔧 **Comandi disponibili:**
/watchlist - Vedi i tuoi prodotti monitorati
/remove <asin> - Rimuovi un prodotto dalla watchlist

Inizia inviando un link Amazon! 🛒"""


def get_product_added_message(title: str, asin: str, price: float = None, currency: str = "EUR", affiliate_link: str = None) -> str:
    """Get message when product is added to watchlist."""
    if price:
        message = f"""✅ Prodotto aggiunto alla watchlist!

📦 **{title}**
🔖 ASIN: `{asin}`
💰 Prezzo iniziale: {price:.2f} {currency}

Il bot monitorerà questo prodotto e ti avviserà quando il prezzo scende! 📉"""
    else:
        message = f"""✅ Prodotto aggiunto alla watchlist!

📦 **{title}**
🔖 ASIN: `{asin}`

Il prodotto è stato aggiunto alla tua watchlist! 📋"""
    
    if affiliate_link:
        message += f"\n\n🔗 [Vedi su Amazon]({affiliate_link})"
    
    return message


def get_product_not_found_message() -> str:
    """Get message when product cannot be found."""
    return """❌ Impossibile trovare il prodotto.

Assicurati di aver inviato un link Amazon valido.
Esempio: https://www.amazon.it/dp/B08N5WRWNW"""


def get_watchlist_message(products: List[Dict]) -> str:
    """Get message with user's watchlist."""
    if not products:
        return """📋 La tua watchlist è vuota.

Invia un link Amazon per aggiungere un prodotto!"""
    
    message = "📋 **La tua watchlist:**\n\n"
    for i, product in enumerate(products, 1):
        title = product.get('title', 'Prodotto senza titolo')
        asin = product.get('asin', 'N/A')
        initial_price = product.get('initial_price')
        currency = product.get('currency', 'EUR')
        target_price = product.get('target_price')
        affiliate_link = product.get('affiliate_link')
        
        message += f"{i}. **{title}**\n"
        message += f"   🔖 ASIN: `{asin}`\n"
        if initial_price:
            message += f"   💰 Prezzo iniziale: {initial_price:.2f} {currency}\n"
        if target_price:
            message += f"   🎯 Prezzo target: {target_price:.2f} {currency}\n"
        if affiliate_link:
            message += f"   🔗 [Vedi su Amazon]({affiliate_link})\n"
        message += "\n"
    
    message += "\nUsa /remove <asin> per rimuovere un prodotto."
    return message


def get_product_removed_message(asin: str) -> str:
    """Get message when product is removed from watchlist."""
    return f"""🗑️ Prodotto rimosso dalla watchlist!

ASIN: `{asin}`

Il prodotto non verrà più monitorato."""


def get_product_not_in_watchlist_message() -> str:
    """Get message when trying to remove a product not in watchlist."""
    return """❌ Prodotto non trovato nella tua watchlist.

Usa /watchlist per vedere i tuoi prodotti monitorati."""


def get_price_drop_notification(product: Dict, old_price: float, new_price: float, 
                                currency: str, affiliate_link: str) -> str:
    """Get notification message when price drops."""
    title = product.get('title', 'Prodotto')
    asin = product.get('asin', 'N/A')
    price_drop = old_price - new_price
    price_drop_percent = (price_drop / old_price) * 100
    
    message = f"""🎉 **Prezzo sceso!**

📦 {title}
🔖 ASIN: `{asin}`

💰 **Prezzo precedente:** {old_price:.2f} {currency}
💰 **Prezzo attuale:** {new_price:.2f} {currency}
📉 **Risparmio:** {price_drop:.2f} {currency} ({price_drop_percent:.1f}%)

🔗 [Acquista ora]({affiliate_link})"""
    
    return message


def get_daily_summary_message(products: List[Dict]) -> str:
    """Get daily summary message with all products in watchlist."""
    if not products:
        return """📋 **Riepilogo Watchlist**

La tua watchlist è vuota.

Invia un link Amazon per aggiungere un prodotto!"""
    
    message = "📋 **Riepilogo Watchlist - Tutti i tuoi prodotti:**\n\n"
    
    for i, product in enumerate(products, 1):
        title = product.get('title', 'Prodotto senza titolo')
        asin = product.get('asin', 'N/A')
        initial_price = product.get('initial_price')
        current_price = product.get('current_price')
        currency = product.get('currency', 'EUR')
        affiliate_link = product.get('affiliate_link', f"https://www.amazon.it/dp/{asin}")
        
        message += f"{i}. **{title}**\n"
        message += f"   🔖 ASIN: `{asin}`\n"
        if initial_price:
            message += f"   💰 Prezzo iniziale: {initial_price:.2f} {currency}\n"
        if current_price:
            message += f"   💵 Prezzo attuale: {current_price:.2f} {currency}\n"
            if initial_price and current_price < initial_price:
                drop = initial_price - current_price
                drop_percent = (drop / initial_price) * 100
                message += f"   📉 Sceso di {drop:.2f} {currency} ({drop_percent:.1f}%)\n"
        message += f"   🔗 [Vedi su Amazon]({affiliate_link})\n"
        message += "\n"
    
    message += "\nUsa /watchlist per vedere i dettagli o /remove <asin> per rimuovere un prodotto."
    return message


def get_error_message() -> str:
    """Get generic error message."""
    return """❌ Si è verificato un errore. Riprova più tardi."""
