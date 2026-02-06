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
    당신은 프로페셔널한 주식 시장 애널리스트입니다. 오늘의 시장 브리핑을 작성해주세요.
    날짜: {today}
    시장: {market_type} (KR=한국, US=미국, GLOBAL=전체)
    
    [내 포트폴리오 요약]
    {json.dumps(portfolio_summary, indent=2)}
    
    [최신 주요 뉴스]
    {market_news}
    
    다음 내용을 포함하여 읽기 편한 한국어 브리핑을 작성해주세요:
    1. **시장 동향**: 뉴스 기반 글로벌/국내 시장 분위기 요약.
    2. **포트폴리오 점검**: 현재 수익률 평가 및 조언.
    3. **오늘의 관전 포인트**: 투자자가 유의해야 할 사항.
    
    이모지(📊, 🚀, 💡 등)를 적절히 사용하여 가독성을 높이고, 마크다운 형식으로 깔끔하게 작성하세요.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Briefing generation failed: {e}"

def analyze_sentiment(stock_name):
    """
    Analyze sentiment for a single stock based on recent news.
    
    Args:
        stock_name (str): Stock name or ticker symbol
        
    Returns:
        tuple: (score, reason) where score is -100 to +100, reason is explanation
    """
    if not model:
        return 0, "AI Not Configured"
    
    # Fetch recent news
    news = get_news(stock_name, max_results=3)
    
    if not news:
        return 0, "No recent news found"
    
    prompt = f"""
    당신은 주식 시장 뉴스 분석 전문가입니다.
    다음 뉴스를 분석하여 '{stock_name}' 종목에 대한 감성 점수를 매겨주세요.
    
    [최근 뉴스]
    {news}
    
    점수 기준:
    - +100: 매우 긍정적 (강력한 매수 신호)
    - +50: 긍정적 (매수 고려)
    - 0: 중립
    - -50: 부정적 (매도 고려)
    - -100: 매우 부정적 (강력한 매도 신호)
    
    응답 형식 (JSON만 반환, 다른 텍스트 없이):
    {{"score": <-100~100 사이 정수>, "reason": "<한 줄 요약>"}}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        return result.get("score", 0), result.get("reason", "분석 완료")
    except Exception as e:
        logging.error(f"Sentiment analysis failed for {stock_name}: {e}")
        return 0, f"분석 실패: {str(e)}"


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
