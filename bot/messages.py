"""Message templates for the Telegram bot."""
from typing import List, Dict
import re


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    # Characters that need escaping in Markdown
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


def get_welcome_message(base_affiliate_link: str = None, user=None, referral_link: str = None) -> str:
    """Get welcome message for /start command."""
    message = """👋 Benvenuto nel Bot Monitor Prezzi Amazon!

📦 **Come funziona:**
1. Invia un link Amazon per aggiungere un prodotto alla watchlist
2. Il bot monitorerà automaticamente il prezzo
3. Riceverai una notifica quando il prezzo scende!
4. Riceverai un riepilogo giornaliero della tua watchlist

🔧 **Comandi disponibili:**
/watchlist - Vedi i tuoi prodotti monitorati
/remove <asin> - Rimuovi un prodotto dalla watchlist
/referral - Vedi le tue statistiche referral

� **Vuoi vedere i migliori sconti del giorno?**
👉 @ScontiAmazonWatchlist

�💡 **Invita amici e diventa VIP:**
• 3 referral = diventi VIP e ricevi notifiche anticipate
• Ogni referral aumenta il limite prodotti"""
    
    if referral_link:
        message += f"\n\n🔗 **Il tuo link referral:**\n`{referral_link}`"
    
    if user and user.is_vip:
        message += "\n\n⭐ Sei VIP! Ricevi notifiche anticipate sugli sconti!"
    
    if base_affiliate_link:
        message += f"\n\n🛍️ [Fai acquisti su Amazon]({base_affiliate_link})"
    
    return message


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
        current_price = product.get('current_price')
        currency = product.get('currency', 'EUR')
        target_price = product.get('target_price')
        affiliate_link = product.get('affiliate_link')
        
        message += f"{i}. **{title}**\n"
        message += f"   🔖 ASIN: `{asin}`\n"
        if initial_price:
            message += f"   💰 Prezzo iniziale: {initial_price:.2f} {currency}\n"
        if current_price:
            message += f"   💵 Prezzo attuale: {current_price:.2f} {currency}\n"
            # Show price change if available
            if initial_price and current_price != initial_price:
                change = current_price - initial_price
                change_percent = (change / initial_price) * 100
                if change < 0:
                    message += f"   📉 Sceso di {abs(change):.2f} {currency} ({abs(change_percent):.1f}%)\n"
                else:
                    message += f"   📈 Salito di {change:.2f} {currency} ({change_percent:.1f}%)\n"
        elif not initial_price:
            message += f"   ⏳ Prezzo non ancora disponibile\n"
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
                                currency: str, affiliate_link: str, bot_username: str = None,
                                price_stats: Dict = None) -> str:
    """Get notification message when price drops with shareable CTA and FOMO messages."""
    import html
    title = product.get('title', 'Prodotto')
    # Escape HTML special characters in title
    title = html.escape(title)
    asin = product.get('asin', 'N/A')
    price_drop = old_price - new_price
    price_drop_percent = (price_drop / old_price) * 100
    
    # Build FOMO messages based on price statistics
    fomo_messages = []
    
    if price_stats:
        # Historical minimum
        if price_stats.get('is_historical_min'):
            fomo_messages.append("📉 <b>Minimo storico Amazon</b>")
        
        # 6-month minimum
        elif price_stats.get('is_6_month_min'):
            fomo_messages.append("⚡ <b>Prezzo mai visto negli ultimi 6 mesi</b>")
        
        # Percentage below average
        if price_stats.get('percent_below_avg') and price_stats['percent_below_avg'] > 10:
            percent = price_stats['percent_below_avg']
            fomo_messages.append(f"💰 <b>{percent:.0f}% sotto la media degli ultimi 6 mesi</b>")
        
        # Days since lowest (if not current minimum)
        if price_stats.get('days_since_lowest') and price_stats['days_since_lowest'] > 0:
            days = price_stats['days_since_lowest']
            if days < 30:
                fomo_messages.append(f"⏰ <b>Prezzo più basso da {days} giorni</b>")
    
    # Add urgency message (time-limited offer simulation)
    # This creates FOMO even if we don't have historical data
    if not fomo_messages:
        fomo_messages.append("⏰ <b>Offerta limitata</b>")
    
    # Build main message
    message = f"""🔥 <b>SCONTO AMAZON</b> 🔥

📦 {title}
🔖 ASIN: <code>{asin}</code>

💰 <b>Prezzo precedente:</b> {old_price:.2f} {currency}
💰 <b>Prezzo attuale:</b> {new_price:.2f} {currency}
📉 <b>Risparmio:</b> {price_drop:.2f} {currency} ({price_drop_percent:.1f}%)"""
    
    # Add FOMO messages
    if fomo_messages:
        message += "\n\n"
        for fomo_msg in fomo_messages:
            message += f"{fomo_msg}\n"
    
    message += f"""
🔗 <a href="{affiliate_link}">Acquista ora</a>

👉 Monitorato con @{bot_username or 'IlTuoBot'}
💡 Ricevi notifiche automatiche sugli sconti

📢 Altri sconti in tempo reale:
👉 @ScontiAmazonWatchlist"""
    
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
    message += "\n\n📢 **Scopri altri sconti:**\n👉 @ScontiAmazonWatchlist"
    return message


def get_error_message() -> str:
    """Get generic error message."""
    return """❌ Si è verificato un errore. Riprova più tardi."""


def get_channel_deal_message(product: Dict, old_price: float, new_price: float, 
                             currency: str, affiliate_link: str, bot_username: str) -> str:
    """Get message for public channel broadcasting."""
    import html
    title = product.get('title', 'Prodotto in offerta')
    # Escape HTML special characters in title
    title = html.escape(title)
    price_drop = old_price - new_price
    price_drop_percent = (price_drop / old_price) * 100
    
    # Ensure title is not too long
    if len(title) > 100:
        title = title[:97] + "..."
    
    message = f"""🔥 <b>SUPER PREZZO!</b>

📦 {title}

❌ Prezzo precedente: {old_price:.2f} {currency}
✅ <b>Prezzo attuale: {new_price:.2f} {currency}</b>
📉 <b>Sconto: -{price_drop_percent:.0f}%</b>

👉 <a href="{affiliate_link}">Link all'offerta</a>

Vuoi monitorare un prodotto?
👉 @{bot_username}"""
    return message


def get_channel_info_message() -> str:
    """Get channel information message for /canale command."""
    return """📢 **Canale ufficiale**

Qui pubblichiamo:
✔ Migliori sconti del giorno
✔ Minimi storici Amazon
✔ Offerte lampo

👉 @ScontiAmazonWatchlist"""
