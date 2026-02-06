import logging
import os
from datetime import datetime
import config
from kis_api import KisApi
import ai_analyst

logging.basicConfig(level=logging.INFO)

def main():
    """Generates a market briefing."""
    logging.info("Starting Briefing Module...")
    kis = KisApi()
    
    # 1. Get Portfolio Status
    holdings, balance = kis.check_balance()
    
    # Simplified summary for AI
    portfolio_summary = {
        "total_balance_krw": balance.get("total_eval", 0),
        "holdings": []
    }
    
    for h in holdings:
        portfolio_summary["holdings"].append({
            "name": h["prdt_name"],
            "qty": h["hldg_qty"],
            "yield": h["evlu_pfls_rt"] + "%"
        })
        
    # 2. Determine Market Type for Briefing
    # Logic: If it's morning (KST 08~09), brief on US close/KR open.
    # If it's evening (KST 15~16), brief on KR close.
    # Currently running on UTC via GitHub Actions, so time check might be tricky.
    # Instead, we just generate for configured markets.
    
    market_type = "GLOBAL"
    if config.MARKET_TYPE == "DOMESTIC": market_type = "KR"
    elif config.MARKET_TYPE == "US": market_type = "US"
    
    logging.info("Generating Briefing...")
    briefing_text = ai_analyst.generate_briefing(market_type, portfolio_summary)
    
    # 3. Save Briefing
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = os.path.join("reports", today)
    os.makedirs(report_dir, exist_ok=True)
    
    filename = f"briefing_{datetime.now().strftime('%H%M')}.md"
    file_path = os.path.join(report_dir, filename)
    
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(f"# 📢 Market Briefing ({today})\n\n")
        f.write(briefing_text)
        
    logging.info(f"Briefing saved to {file_path}")
    
    # 4. Discord Notification
    import discord_notifier
    discord_notifier.send_message(f"📢 **Market Briefing ({market_type})**\n\n{briefing_text[:1900]}...", type="briefing")

if __name__ == "__main__":
    main()
