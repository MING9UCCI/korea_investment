import requests
import config
import logging

def send_message(message, type="trading"):
    """
    Send a message to the configured Discord Webhook.
    type: "trading" or "briefing"
    """
    if type == "briefing":
        url = config.DISCORD_WEBHOOK_BRIEFING
    else:
        url = config.DISCORD_WEBHOOK_TRADING
        
    # Fallback: If specific url missing, try the other, or fail
    if not url:
        if type == "trading" and config.DISCORD_WEBHOOK_BRIEFING: url = config.DISCORD_WEBHOOK_BRIEFING
        elif type == "briefing" and config.DISCORD_WEBHOOK_TRADING: url = config.DISCORD_WEBHOOK_TRADING
    
    if not url:
        logging.warning(f"Discord Webhook URL not set for {type}. Skipping.")
        return False
        
    payload = {
        "content": message
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"Failed to send Discord message: {e}")
        return False

if __name__ == "__main__":
    send_message("📢 Trading Alert Test", type="trading")
    send_message("📢 Briefing Report Test", type="briefing")
