import pandas as pd
from strategies.base_strategy import BaseStrategy

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

class MeanReversionStrategy(BaseStrategy):
    def __init__(self, params):
        super().__init__("MeanReversion", params)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_lower = self.params.get('rsi_lower', 30)
        self.rsi_upper = self.params.get('rsi_upper', 70)
        self.take_profit_pct = self.params.get('take_profit_pct', 5.0)
        self.stop_loss_pct = self.params.get('stop_loss_pct', -2.0)

    def analyze(self, df: pd.DataFrame, current_holdings: list, target_code: str) -> tuple[str, str, float]:
        if df.empty or len(df) < self.rsi_period:
            return "HOLD", "Not enough data", 0.0

        df['RSI'] = calculate_rsi(df['Close'], self.rsi_period)
        latest = df.iloc[-1]
        
        holding_info = None
        for h in current_holdings:
            if h.get('pdno') == target_code:
                holding_info = h
                break

        if holding_info:
            profit_pct = float(holding_info.get('evlu_pfls_rt', 0.0))
            if profit_pct <= self.stop_loss_pct:
                return "SELL", f"Stop Loss ({profit_pct:.2f}%)", 0.0
            if profit_pct >= self.take_profit_pct or latest['RSI'] > self.rsi_upper:
                return "SELL", f"Overbought Take Profit (RSI: {latest['RSI']:.1f})", 0.0
            return "HOLD", f"Holding (RSI: {latest['RSI']:.1f}, Profit: {profit_pct:.2f}%)", 0.0

        if latest['RSI'] < self.rsi_lower:
            return "BUY", f"Deep Oversold Reversion (RSI: {latest['RSI']:.1f} < {self.rsi_lower})", 0.05
            
        return "HOLD", f"No Signal (RSI: {latest['RSI']:.1f})", 0.0
