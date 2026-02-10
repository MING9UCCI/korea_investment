import time
import logging
import pandas as pd
import os
import json
from datetime import datetime
import config
from kis_api import KisApi
import strategy
import market_schedule
import ai_analyst
import discord_notifier
import chart_generator

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
    """Generate HTML report stored in date-based directory (Cumulative)."""
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = os.path.join("reports", today)
    os.makedirs(report_dir, exist_ok=True)
    
    # 1. Load/Update Daily Log (JSON)
    log_file = os.path.join(report_dir, "trade_log.json")
    daily_log = []
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                daily_log = json.load(f)
        except Exception as e:
            logging.error(f"Failed to load existing log: {e}")
            
    # Append new results with timestamp
    current_time = datetime.now().strftime("%H:%M:%S")
    for res in results:
        res['timestamp'] = current_time
        daily_log.append(res)
        
    # Save updated log
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(daily_log, f, ensure_ascii=False, indent=2)
        
    # 2. Generate Cumulative HTML Report
    html = f"""
    <html>
    <head>
        <title>Trading Report - {today}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }}
            h1 {{ color: #4a4a4a; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
            .summary {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #667eea; color: white; font-weight: 600; text-transform: uppercase; font-size: 0.9em; }}
            tr:hover {{ background-color: #f1f1f1; }}
            .buy {{ color: #e53e3e; font-weight: bold; }}
            .sell {{ color: #3182ce; font-weight: bold; }}
            .hold {{ color: #718096; }}
            .timestamp {{ color: #718096; font-size: 0.9em; }}
            .no-action {{ color: #a0aec0; font-style: italic; }}
        </style>
    </head>
    <body>
    <h1>📅 Daily Trading Report ({today})</h1>
    
    <div class="summary">
        <p><strong>Total Scans:</strong> {len(daily_log)}</p>
        <p><strong>Last Update:</strong> {current_time}</p>
        <a href="/history" style="text-decoration: none; color: #667eea; font-weight: bold;">View History &rarr;</a>
    </div>

    <table>
    <thead>
        <tr>
            <th>Time</th>
            <th>Market</th>
            <th>Code</th>
            <th>Name</th>
            <th>Signal</th>
            <th>AI Score</th>
            <th>Reason</th>
            <th>Action</th>
        </tr>
    </thead>
    <tbody>
    """
    
    # Sort log by time (newest first)
    for res in reversed(daily_log):
        signal_class = "buy" if res['signal'] == "BUY" else "sell" if res['signal'] == "SELL" else "hold"
        ai_score = res.get('ai_score', 'N/A')
        name = res.get('name', res['code'])
        
        html += f"""
        <tr>
            <td class="timestamp">{res['timestamp']}</td>
            <td>{res['market']}</td>
            <td>{res['code']}</td>
            <td>{name}</td>
            <td class="{signal_class}">{res['signal']}</td>
            <td>{ai_score}</td>
            <td>{res['reason']}</td>
            <td>{res['action']}</td>
        </tr>
        """
        
    html += "</tbody></table></body></html>"
    
    file_path = os.path.join(report_dir, "report.html")
    with open(file_path, "w", encoding='utf-8') as f:
        f.write(html)
    logging.info(f"Cumulative Report generated: {file_path}")

    
    
    # Send Discord Notification
    # Group results by market or action type for better readability
    executed_trades = []
    for res in results:
        if "Executed" in res['action']:
            executed_trades.append(res)

    # Only send if there are executed trades
    if executed_trades:
        mode_label = "모의투자" if config.KIS_MODE == "VIRTUAL" else "실전투자"
        current_time = datetime.now().strftime("%H:%M")
        msg = f"⚡ **[{today} {current_time}] 매매 체결 알림 ({mode_label})** ⚡\n\n"
        
        msg += "**✅ 체결 내역**\n"
        for res in executed_trades:
            emoji = "🔴 매수" if "BUY" in res['signal'] else "🔵 매도"
            msg += f"> {emoji} **{res['name']}** ({res['code']})\n"
            msg += f"> `사유` {res['reason']}"
            if res.get('ai_link'):
                msg += f" ([뉴스보기]({res['ai_link']}))"
            msg += "\n\n"
            
        msg += "👉 [상세 리포트/자산 그래프](https://ming9ucci.github.io/korea_investment/)\n"
        discord_notifier.send_message(msg, type="trading")
        
        # Send Chart Images for Executed Trades
        for res in executed_trades:
            if res.get('chart_path'):
                caption = f"📉 {res['name']} ({res['code']}) 매매 차트"
                discord_notifier.send_message(caption, type="trading", file_path=res['chart_path'])
    else:
        logging.info("No trades executed. Skipping Discord notification.")

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
                    ai_score, ai_reason, ai_link = ai_analyst.analyze_sentiment(name)
                    reason += f" | AI: {ai_reason}"
                    
                    # Hybrid Logic: Overrule if AI is strongly opposing
                    if signal == "BUY" and ai_score < -50:  # More lenient (was -20)
                        logging.warning(f"[{code}] AI VETO: BUY blocked (AI score: {ai_score})")
                        signal = "HOLD"
                        reason += " (AI Veto: Very Negative News)"
                    elif signal == "SELL" and ai_score > 20:
                        pass # Let technical sell proceed even with generic positive news
                
                logging.info(f"[{name}] Signal: {signal} | AI Score: {ai_score}")
                
                action = "None"
                
                # 4. Execute
                chart_path = None
                if signal == "BUY":
                    if kis.buy_order(code, 1):
                        action = "Executed BUY"
                        chart_path = chart_generator.generate_chart(df, code, name, "BUY")
                    else:
                        action = "Failed BUY"
                elif signal == "SELL":
                    if kis.sell_order(code, 1):
                         action = "Executed SELL"
                         chart_path = chart_generator.generate_chart(df, code, name, "SELL")
                    else:
                        action = "Failed SELL"
                
                results.append({
                    "market": "KR", "code": code, "name": name, "signal": signal, "ai_score": ai_score, "reason": reason, "ai_link": ai_link if 'ai_link' in locals() else "", "action": action, "chart_path": chart_path
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
                    ai_score, ai_reason, ai_link = ai_analyst.analyze_sentiment(code)
                    reason += f" | AI: {ai_reason}"
                    
                    if signal == "BUY" and ai_score < -50:  # Less restrictive (was -20)
                        signal = "HOLD"
                        reason += " (AI Veto: Very Negative News)"
                
                logging.info(f"[{code}] US Signal: {signal} | AI Score: {ai_score}")
                
                action = "None"
                
                # 4. Execute
                chart_path = None
                if signal == "BUY":
                    if kis.buy_overseas_order(code, 1, excd):
                        action = "Executed US BUY"
                        chart_path = chart_generator.generate_chart(df, code, name, "BUY")
                    else:
                        action = "Failed US BUY"
                elif signal == "SELL":
                    if kis.sell_overseas_order(code, 1, excd):
                        action = "Executed US SELL"
                        chart_path = chart_generator.generate_chart(df, code, name, "SELL")
                    else:
                        action = "Failed US SELL"
                
                results.append({
                    "market": "US", "code": code, "name": name, "signal": signal, "ai_score": ai_score, "reason": reason, "ai_link": ai_link if 'ai_link' in locals() else "", "action": action, "chart_path": chart_path
                })
                time.sleep(0.5)
        else:
            logging.info("=== US Market is Closed (Holiday/Weekend) ===")
    
    generate_report(results)
    logging.info("Trading Cycle Completed.")

if __name__ == "__main__":
    main()
