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

def calculate_macd(series, fast=12, slow=26, signal=9):
    """Calculate MACD, Signal Line, and Histogram."""
    exp1 = series.ewm(span=fast, adjust=False).mean()
    exp2 = series.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

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
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['Close'])
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Strategy Logic (Trend + Mean Reversion)
    # Buy: 
    #   1. (RSI < 40 AND MACD > Signal) = Momentum Reversal
    #   2. (RSI < 30) = Deep Oversold (Dip Buy)
    # Sell:
    #   1. (RSI > 70) = Overbought
    #   2. (MACD < Signal AND RSI > 60) = Momentum Breakdown
    
    rsi = latest['RSI']
    price = latest['Close']
    bb_lower = latest['BB_Lower']
    bb_upper = latest['BB_Upper']
    macd = latest['MACD']
    macd_signal = latest['MACD_Signal']
    macd_hist = latest['MACD_Hist']
    
    signal = "HOLD"
    reason = f"RSI:{rsi:.1f} MACD:{macd_hist:.1f}"

    # BUY Logic
    if rsi < 30:
        signal = "BUY"
        reason = f"Deep Oversold (RSI {rsi:.1f})"
    elif rsi < 45 and macd > macd_signal and latest['MACD_Hist'] > prev['MACD_Hist']: # Momentum turning up
        signal = "BUY"
        reason = f"Trend Reversal (RSI {rsi:.1f}, MACD Bullish)"
    elif price <= bb_lower * 1.01 and rsi < 50: # Bollinger Band bounce
        signal = "BUY"
        reason = f"BB Lower Bounce (RSI {rsi:.1f})"

    # SELL Logic
    elif rsi > 70:
         signal = "SELL"
         reason = f"Overbought (RSI {rsi:.1f})"
    elif macd < macd_signal and rsi > 60:
         signal = "SELL"
         reason = f"Momentum Loss (MACD Bearish)"
    elif price >= bb_upper * 0.99:
         signal = "SELL"
         reason = f"BB Upper Resistance"

    return signal, reason
