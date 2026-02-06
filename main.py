import time
import logging
import pandas as pd
import os
from datetime import datetime
import config
from kis_api import KisApi
import strategy
import market_schedule

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trade.log"),
        logging.StreamHandler()
    ]
)

def generate_report(results):
    """Generate HTML report stored in date-based directory."""
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = os.path.join("reports", today)
    os.makedirs(report_dir, exist_ok=True)
    
    html = f"""
    <html>
    <head>
        <title>Trading Report - {today}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .buy {{ color: red; font-weight: bold; }}
            .sell {{ color: blue; font-weight: bold; }}
        </style>
    </head>
    <body>
    <h1>Daily Trading Report ({today})</h1>
    <a href="/history">View History</a>
    <table border="1">
    <tr><th>Market</th><th>Code</th><th>Signal</th><th>Reason</th><th>Action</th></tr>
    """
    for res in results:
        signal_class = "buy" if res['signal'] == "BUY" else "sell" if res['signal'] == "SELL" else ""
        html += f"<tr><td>{res['market']}</td><td>{res['code']}</td><td class='{signal_class}'>{res['signal']}</td><td>{res['reason']}</td><td>{res['action']}</td></tr>"
    html += "</table></body></html>"
    
    file_path = os.path.join(report_dir, "report.html")
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(html)
    logging.info(f"Report generated: {file_path}")
    
    
    # Send Discord Notification
    # Send Discord Notification
    mode_label = "모의투자" if config.KIS_MODE == "VIRTUAL" else "실전투자"
    msg = f"📊 **[{today}] 데일리 트레이딩 리포트 ({mode_label})** 📊\n\n"
    has_action = False
    
    # Group results by market or action type for better readability
    executed_trades = []
    failed_trades = []
    
    for res in results:
        if "Executed" in res['action']:
            executed_trades.append(res)
        elif "Failed" in res['action']:
            failed_trades.append(res)

    if executed_trades:
        has_action = True
        msg += "**✅ 체결 내역**\n"
        for res in executed_trades:
            emoji = "🔴 매수" if "BUY" in res['signal'] else "🔵 매도"
            msg += f"> {emoji} **{res['name']}**\n"
            msg += f"> `사유` {res['reason']}\n\n"
            
    if failed_trades:
        # Only report failures if needed, or keep it silent to reduce noise
        pass 
            
    if has_action:
        msg += f"\n👉 [상세 리포트 확인하기](https://github.com/Minwoo/korea_investment/actions)"
        discord_notifier.send_message(msg, type="trading")

def main():
    logging.info("Starting Trading Bot...")
    kis = KisApi()
    
    results = []
    
    # Check Balance
    holdings, balance_summary = kis.check_balance()
    if not balance_summary and not holdings:
        logging.error("CRITICAL: Failed to fetch balance. Check API Keys or Account Number.")
        # Proceeding might be dangerous if we don't know balance, but for now just log
        
    logging.info(f"Current Balance Summary: {balance_summary}")
    # --- Domestic Trading ---
    if config.MARKET_TYPE in ["DOMESTIC", "BOTH"]:
        if market_schedule.is_kr_market_open():
            logging.info("=== Starting Domestic Market Trading ===")
            # Determine Domestic Targets
            if config.USE_MARKET_SCAN:
                logging.info(f"Scanning Domestic Market for Top {config.SCAN_LIMIT} Volume Stocks...")
                domestic_targets = kis.get_volume_rank(limit=config.SCAN_LIMIT)
                logging.info(f"Found {len(domestic_targets)} domestic targets.")
            else:
                domestic_targets = config.TARGET_CODES
                logging.info(f"Using fixed domestic targets: {domestic_targets}")
            
            for code in domestic_targets:
                logging.info(f"[Domestic] Analyzing {code}...")
                # Get Name for AI
                curr_price = kis.get_current_price(code)
                name = curr_price['name'] if curr_price else code
                
                # 1. Get History
                df = kis.get_market_price_history(code)
                if df.empty:
                    logging.error(f"Failed to fetch history for {code}")
                    continue
                    
                # 2. Analyze (Technical)
                signal, reason = strategy.analyze_stock(df)
                
                # 3. Analyze (AI) - Only if signal is active to save quotas
                ai_score = 0
                ai_reason = "Skipped"
                if signal in ["BUY", "SELL"]:
                    logging.info(f"Technical signal found for {name}. Asking AI...")
                    ai_score, ai_reason = ai_analyst.analyze_sentiment(name)
                    reason += f" | AI: {ai_reason}"
                    
                    # Hybrid Logic: Overrule if AI is strongly opposing
                    if signal == "BUY" and ai_score < -20:
                        signal = "HOLD"
                        reason += " (AI Veto: Negative News)"
                    elif signal == "SELL" and ai_score > 20:
                        pass # Let technical sell proceed even with generic positive news
                
                logging.info(f"[{name}] Signal: {signal} | AI Score: {ai_score}")
                
                action = "None"
                
                # 4. Execute
                if signal == "BUY":
                    if kis.buy_order(code, 1):
                        action = "Executed BUY"
                    else:
                        action = "Failed BUY"
                elif signal == "SELL":
                    if kis.sell_order(code, 1):
                         action = "Executed SELL"
                    else:
                        action = "Failed SELL"
                
                results.append({
                    "market": "KR", "code": code, "name": name, "signal": signal, "ai_score": ai_score, "reason": reason, "action": action
                })
                time.sleep(0.5)
        else:
             logging.info("=== Domestic Market is Closed (Holiday/Weekend) ===")

    # --- US Trading ---
    if config.MARKET_TYPE in ["US", "BOTH"]:
        if market_schedule.is_us_market_open():
            logging.info("=== Starting US Market Trading ===")
            us_targets = config.US_TARGET_CODES
            logging.info(f"Using US targets: {us_targets}")
            
            for code in us_targets:
                logging.info(f"[US] Analyzing {code}...")
                name = code # US tickers are usually the search term
                
                # 1. Get History
                # Default to NASDAQ (NAS) for tech stocks in list.
                # Ideally config should map code to exchange.
                excd = "NAS" 
                if code == "NYS": excd = "NYS" # Simple hack if needed, but for now allow all NAS
                
                df = kis.get_overseas_history(code, excd)
                if df.empty:
                    logging.error(f"Failed to fetch US history for {code}")
                    continue
                
                # 2. Analyze
                signal, reason = strategy.analyze_stock(df)
                
                # 3. Analyze (AI)
                ai_score = 0
                ai_reason = "Skipped"
                if signal in ["BUY", "SELL"]:
                    logging.info(f"Technical signal found for {code}. Asking AI...")
                    ai_score, ai_reason = ai_analyst.analyze_sentiment(code)
                    reason += f" | AI: {ai_reason}"
                    
                    if signal == "BUY" and ai_score < -20:
                        signal = "HOLD"
                        reason += " (AI Veto: Negative News)"
                
                logging.info(f"[{code}] US Signal: {signal} | AI Score: {ai_score}")
                
                action = "None"
                
                # 4. Execute
                if signal == "BUY":
                    if kis.buy_overseas_order(code, 1, excd):
                        action = "Executed US BUY"
                    else:
                        action = "Failed US BUY"
                elif signal == "SELL":
                    if kis.sell_overseas_order(code, 1, excd):
                        action = "Executed US SELL"
                    else:
                        action = "Failed US SELL"
                
                results.append({
                    "market": "US", "code": code, "name": name, "signal": signal, "ai_score": ai_score, "reason": reason, "action": action
                })
                time.sleep(0.5)
        else:
            logging.info("=== US Market is Closed (Holiday/Weekend) ===")
    
    generate_report(results)
    logging.info("Trading Cycle Completed.")

if __name__ == "__main__":
    main()
