"""
Daily Performance Summary Script
Calculates and reports daily trading performance at market close
"""
import os
import json
from datetime import datetime
import config
import discord_notifier

def calculate_daily_performance():
    """Calculate daily performance from today's reports"""
    today = datetime.now().strftime("%Y-%m-%d")
    report_dir = os.path.join("reports", today)
    
    if not os.path.exists(report_dir):
        print(f"No reports found for {today}")
        return
    
    # Read all HTML reports from today
    total_buys = 0
    total_sells = 0
    trades = []
    
    # This is a simplified version - in production, you'd parse the HTML
    # or maintain a JSON log of trades
    
    # For now, send a summary message
    mode_label = "모의투자" if config.KIS_MODE == "VIRTUAL" else "실전투자"
    
    msg = f"📊 **[{today}] 일일 종합 리포트 ({mode_label})** 📊\\n\\n"
    msg += "---\\n\\n"
    msg += "**📈 오늘의 거래 요약**\\n"
    msg += f"> 매수: {total_buys}건\\n"
    msg += f"> 매도: {total_sells}건\\n\\n"
    msg += "---\\n\\n"
    msg += "💡 _상세 수익률은 KIS 앱에서 확인하세요_"
    
    discord_notifier.send_message(msg, type="trading")
    print(f"Daily summary sent for {today}")

if __name__ == "__main__":
    calculate_daily_performance()
