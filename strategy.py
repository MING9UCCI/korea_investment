import pandas as pd
import config

def calculate_rsi(series, period=14):
    """Calculate Relative Strength Index."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(series, period=20, std=2):
    """Calculate Bollinger Bands."""
    ma = series.rolling(window=period).mean()
    sigma = series.rolling(window=period).std()
    upper = ma + (sigma * std)
    lower = ma - (sigma * std)
    return upper, ma, lower

def analyze_stock(df):
    """
    Analyze a stock DataFrame and return the latest signal.
    df requires columns: ['Close']
    """
    if df.empty or len(df) < 30: # Need enough data
        return "HOLD", "Not enough data"

    # Calculate Indicators
    df['RSI'] = calculate_rsi(df['Close'], config.RSI_PERIOD)
    df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'], config.BB_PERIOD, config.BB_STD)
    
    latest = df.iloc[-1]
    
    # Strategy Logic
    # Buy: RSI < Lower Threshold (Oversold) AND Price <= BB Lower Limit (optional confirmation)
    # Sell: RSI > Upper Threshold (Overbought) OR Price >= BB Upper Limit
    
    rsi = latest['RSI']
    price = latest['Close']
    bb_lower = latest['BB_Lower']
    bb_upper = latest['BB_Upper']
    
    signal = "HOLD"
    reason = f"RSI: {rsi:.2f}, Price: {price}, BB_Low: {bb_lower:.2f}, BB_High: {bb_upper:.2f}"

    if rsi < config.RSI_LOWER:
        if price <= bb_lower * 1.02: # Within 2% of lower band
            signal = "BUY"
            reason = f"Oversold (RSI {rsi:.2f}) & Near BB Lower"
            
    elif rsi > config.RSI_UPPER:
         if price >= bb_upper * 0.98: # Within 2% of upper band
            signal = "SELL"
            reason = f"Overbought (RSI {rsi:.2f}) & Near BB Upper"

    return signal, reason
