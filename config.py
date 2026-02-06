import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# [Brokerage / Account Settings]
# This bot is designed for 'Korea Investment & Securities' (KIS).
# You must have a KIS account and Open API Key.
APP_KEY = os.getenv("KIS_APP_KEY", "YOUR_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET", "YOUR_APP_SECRET")

# [AI Settings]
# Google Gemini API Key (Free Tier available)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_KEY")

# [Discord Settings]
# If you want separate channels, set both. If same, put same URL.
DISCORD_WEBHOOK_TRADING = os.getenv("DISCORD_WEBHOOK_TRADING", "")
DISCORD_WEBHOOK_BRIEFING = os.getenv("DISCORD_WEBHOOK_BRIEFING", "")

# 'Seed Money' is the cash in this account.
CANO = os.getenv("KIS_CANO", "YOUR_ACCOUNT_NO") # Account Number (8 digits)
ACNT_PRDT_CD = os.getenv("KIS_ACNT_PRDT_CD", "01") # Account Product Code (usually 01)

# API URLs (Real vs Virtual)
# Use 'VIRTUAL' for paper trading with mock money.
# Use 'REAL' for actual trading with your real money.
MODE = os.getenv("KIS_MODE", "VIRTUAL") 
URL_BASE = "https://openapi.koreainvestment.com:9443" if MODE == "REAL" else "https://openapivts.koreainvestment.com:29443"

# [Target Settings]
# Market Type: "DOMESTIC", "US", or "BOTH"
MARKET_TYPE = "BOTH" 

# If USE_MARKET_SCAN is True, the bot ignores TARGET_CODES and picks Top 100 by Volume.
# (Note: Market Scan currently only supports Domestic. US will use fixed list below for now)
USE_MARKET_SCAN = True 
SCAN_LIMIT = 50 

# If USE_MARKET_SCAN is False (or for US stocks), these codes are used:
TARGET_CODES = ["005930", "000660"] # Domestic: Samsung Elec, SK Hynix
# NOTE: Major US Tech stocks (TSLA, AAPL) cost > $200 (approx 300,000 KRW). 
# With 10,000 KRW seed, you cannot buy 1 share in REAL mode. Use VIRTUAL mode to test.
US_TARGET_CODES = ["TSLA", "AAPL", "NVDA", "MSFT"] # US: Tesla, Apple, Nvidia, Microsoft

# [Strategy Parameters]
RSI_PERIOD = 14
RSI_LOWER = 30
RSI_UPPER = 70
BB_PERIOD = 20
BB_STD = 2

# [Reporting]
REPORT_FILE = "daily_report.html"
