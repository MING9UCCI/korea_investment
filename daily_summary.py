"""
Daily Performance Summary Script
Calculates and reports daily trading performance at market close
"""
import os
import json
from datetime import datetime
import config
import discord_notifier
from kis_api import KisApi

def calculate_daily_performance():
    """Calculate daily performance and update summary JSON"""
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = os.path.join("reports", today)
    
    # Initialize KIS API to fetch current balance
    kis = KisApi()
    balance_info = kis.check_balance()
    
    # Calculate Total Assets
    # balance_info usually contains: {'deposit': ..., 'total_eval': ..., 'pnl': ...}
    # We need to be careful about the exact keys returned by check_balance
    # Based on kis_api.py, check_balance returns (holdings, summary) or just summary in some versions?
    # Checking kis_api.py: return holdings, summary
    
    holdings, summary = balance_info
    
    # Extract key metrics safely
    try:
        # Note: KIS API keys might differ based on real/virtual. 
        # Usually:
        # dnca_tot_amt = 예수금 (Deposit)
        # evlu_amt_smtl_amt = 평가금액 (Eval Amount)
        # tot_evlu_amt = 총평가금액 (Total Eval)
        
        # summary dictionary from kis_api.py check_balance usually has keys like:
        # 'dnca_tot_amt', 'tot_evlu_mamt', 'nass_amt' (Net Asset)
        
        current_balance = int(summary.get('dnca_tot_amt', 0))
        total_eval = int(summary.get('tot_evlu_mamt', 0))
        net_asset = int(summary.get('nass_amt', 0)) # Net Asset Value
        
        # If nass_amt is 0 (sometimes happens), use balance + eval
        if net_asset == 0:
            net_asset = current_balance + total_eval
            
        profit_loss = int(summary.get('evlu_pfls_smtl_amt', 0)) # Profit/Loss
        
    except Exception as e:
        print(f"Error parsing balance summary: {e}")
        net_asset = 0
        profit_loss = 0

    # Load Cumulative Daily Log (daily_summary.json in root or reports?)
    # Root is better for historical tracking across days
    log_file = "daily_summary.json"
    daily_data = []
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                daily_data = json.load(f)
        except Exception as e:
            print(f"Error loading daily_summary.json: {e}")
            
    # Check if entry for today already exists, update it if so
    entry = {
        "date": today,
        "net_asset": net_asset,
        "profit_loss": profit_loss,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    
    # Remove existing entry for today if exists (to update)
    daily_data = [d for d in daily_data if d['date'] != today]
    daily_data.append(entry)
    
    # Sort by date
    daily_data.sort(key=lambda x: x['date'])
    
    # Save Log
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(daily_data, f, ensure_ascii=False, indent=2)
        
    print(f"Updated {log_file} with Net Asset: {net_asset}, P/L: {profit_loss}")
    
    # Generate Daily Briefing Message
    mode_label = "모의투자" if config.KIS_MODE == "VIRTUAL" else "실전투자"
    
    # Calculate daily change if possible
    prev_asset = daily_data[-2]['net_asset'] if len(daily_data) > 1 else net_asset
    daily_diff = net_asset - prev_asset
    emoji_diff = "🔺" if daily_diff > 0 else "🔻" if daily_diff < 0 else "➖"
    
    msg = f"📊 **[{today}] 마감 자산 리포트 ({mode_label})** 📊\n\n"
    msg += f"💰 **총 자산**: {net_asset:,}원 ({emoji_diff} {daily_diff:,}원)\n"
    msg += f"💵 **평가 손익**: {profit_loss:,}원\n"
    msg += f"📈 **보유 종목**: {len(holdings)}개\n\n"
    
    if holdings:
        msg += "**[보유 종목 TOP 3]**\n"
        # Sort holdings by evaluation amount desc
        sorted_holdings = sorted(holdings, key=lambda x: int(x.get('evlu_amt', 0)), reverse=True)[:3]
        for h in sorted_holdings:
            name = h.get('prdt_name', 'Unknown')
            qty = h.get('hldg_qty', 0)
            yield_rt = h.get('evlu_pfls_rt', 0)
            msg += f"> {name} ({qty}주): {yield_rt}%\n"
            
    msg += "\n---\n"
    msg += "👉 [자산 그래프 확인하기](https://ming9ucci.github.io/korea_investment/)\n"
    
    discord_notifier.send_message(msg, type="trading")
    print(f"Daily summary sent for {today}")

if __name__ == "__main__":
    calculate_daily_performance()
