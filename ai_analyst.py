import google.generativeai as genai
from gnews import GNews
import config
import logging
import json
from datetime import datetime

# Initialize Gemini
if config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
    # User confirmed Gemini 2.5 Flash exists.
    model = genai.GenerativeModel('gemini-2.5-flash') 
else:
    model = None
    logging.warning("GEMINI_API_KEY not found. AI analysis will be disabled.")

def get_news(keyword, max_results=3):
    """Fetch news from Google News RSS."""
    google_news = GNews(language='en', country='US', period='1d', max_results=max_results)
    # Check if keyword is Korean
    if any("\u3130" <= char <= "\u318f" or "\uac00" <= char <= "\ud7a3" for char in keyword):
        google_news.language = 'ko'
        google_news.country = 'KR'
        
    try:
        news_list = google_news.get_news(keyword)
        simplified_news = []
        for news in news_list:
            pub_date = news.get('published date', '')
            title = news.get('title', '')
            link = news.get('url', '')
            simplified_news.append(f"- [{pub_date}] {title} ({link})")
        return "\n".join(simplified_news)
    except Exception as e:
        logging.error(f"Failed to fetch news for {keyword}: {e}")
        return ""

def generate_briefing(market_type, portfolio_summary):
    """Generate Morning/Closing Briefing."""
    if not model:
        return "AI Not Configured"
        
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Fetch general market news
    market_keywords = "stock market news" if market_type == "US" else "한국 주식 시장 뉴스"
    market_news = get_news(market_keywords, max_results=5)
    
    prompt = f"""
    You are a professional financial analyst writing a daily briefing.
    Date: {today}
    Market: {market_type}
    
    [My Portfolio Summary]
    {json.dumps(portfolio_summary, indent=2)}
    
    [Latest Market News]
    {market_news}
    
    Write a concise briefing (in Korean) that covers:
    1. Global/Local market sentiment based on news.
    2. Review of my portfolio performance.
    3. Key things to watch today.
    
    Format nicely with Markdown.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Briefing generation failed: {e}"

def analyze_portfolio(holdings, candidates, balance):
    """
    Analyze the entire portfolio and candidates to decide trades.
    
    Args:
        holdings (list): List of dicts {code, name, qty, price, yield, news}
        candidates (list): List of dicts {code, name, price, rsi, news}
        balance (float): Current available cash (KRW)
        
    Returns:
        list: List of decisions [{action: BUY/SELL/HOLD, code: ..., reason: ...}]
    """
    if not model:
        return []

    # Construct Context
    context = {
        "cash_balance": balance,
        "holdings": holdings,
        "candidates": candidates
    }
    
    prompt = f"""
    You are an AI Portfolio Manager. Your goal is to maximize profit and minimize risk.
    Current Balance: {balance} KRW.
    
    [Current Holdings]
    {json.dumps(holdings, indent=2, ensure_ascii=False)}
    
    [Market Candidates (Top Volume / Watchlist)]
    {json.dumps(candidates, indent=2, ensure_ascii=False)}
    
    [Task]
    Analyze the holdings and candidates based on their Technical (RSI) and Fundamental (News) data.
    Decide whether to:
    1. SELL existing holdings (if bad news, overbought, or better opportunity exists).
    2. BUY new candidates (if good news, oversold, and momentum exists).
    3. HOLD (if uncertainty is high).
    
    Constraints:
    - Do not spend more than available cash.
    - If a candidate has very negative news, DO NOT BUY.
    - If a holding has very negative news, SELL immediately.
    - You can sell a holding to buy a better candidate (Switching).
    
    Return the result ONLY as a JSON list of actions. No markdown, no explanation text outside JSON.
    Example format:
    [
        {{"action": "SELL", "code": "005930", "qty": 10, "reason": "Bad earnings news and RSI overbought"}},
        {{"action": "BUY", "code": "TSLA", "qty": 1, "reason": "Strong positive momentum and oversold"}}
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        decisions = json.loads(text)
        return decisions
    except Exception as e:
        logging.error(f"Portfolio analysis failed: {e}")
        return []
