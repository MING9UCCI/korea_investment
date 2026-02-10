import mplfinance as mpf
import pandas as pd
import os
from datetime import datetime

def generate_chart(df, code, name, signal, output_dir="reports/images"):
    """
    Generate a candle chart for the given stock data.
    
    Args:
        df (pd.DataFrame): Stock history with 'open', 'high', 'low', 'close', 'volume' columns.
        code (str): Stock code.
        name (str): Stock name.
        signal (str): BUY or SELL signal for title/color.
        output_dir (str): Directory to save the image.
        
    Returns:
        str: Absolute path to the saved image file, or None if failed.
    """
    try:
        # ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare Data
        # Ensure index is DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
            
        # Ensure columns are float
        cols = ['open', 'high', 'low', 'close', 'volume']
        for col in cols:
            if col in df.columns:
                df[col] = df[col].astype(float)
                
        # Style settings
        mc = mpf.make_marketcolors(up='r', down='b', inherit=True)
        s  = mpf.make_mpf_style(marketcolors=mc, gridstyle=':', y_on_right=True)
        
        # Title
        title = f"{name} ({code}) - {signal}"
        
        # Filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{code}_{signal}_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)
        
        # Plot (Last 60 candles)
        plot_df = df.tail(60)
        
        mpf.plot(
            plot_df,
            type='candle',
            mav=(5, 20),
            volume=True,
            title=title,
            style=s,
            savefig=dict(fname=filepath, dpi=100, pad_inches=0.25)
        )
        
        print(f"Chart generated: {filepath}")
        return os.path.abspath(filepath)
        
    except Exception as e:
        print(f"Failed to generate chart for {code}: {e}")
        return None

if __name__ == "__main__":
    # Test
    # Create dummy dataframe
    dates = pd.date_range(end=datetime.now(), periods=60)
    data = {
        'open': [1000 + x for x in range(60)],
        'high': [1010 + x for x in range(60)],
        'low': [990 + x for x in range(60)],
        'close': [1005 + x for x in range(60)],
        'volume': [1000 for _ in range(60)]
    }
    df = pd.DataFrame(data, index=dates)
    generate_chart(df, "005930", "TestStock", "BUY")
