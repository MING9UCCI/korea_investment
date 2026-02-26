import pandas as pd
from strategies.base_strategy import BaseStrategy

class TrendFollowingStrategy(BaseStrategy):
    def __init__(self, params):
        # 템플릿의 내용: {ma_fast: 5, ma_slow: 20, take_profit_pct: 7.0, stop_loss_pct: -3.0, trailing_stop_pct: -2.0}
        super().__init__("TrendFollowing", params)
        self.ma_fast_period = self.params.get('ma_fast', 5)
        self.ma_slow_period = self.params.get('ma_slow', 20)
        self.take_profit_pct = self.params.get('take_profit_pct', 7.0)
        self.stop_loss_pct = self.params.get('stop_loss_pct', -3.0)
        
    def analyze(self, df: pd.DataFrame, current_holdings: list, target_code: str) -> tuple[str, str, float]:
        if df.empty or len(df) < self.ma_slow_period:
            return "HOLD", "Not enough data", 0.0

        # 이동평균선 계산
        df['MA_Fast'] = df['Close'].rolling(window=self.ma_fast_period).mean()
        df['MA_Slow'] = df['Close'].rolling(window=self.ma_slow_period).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        price = latest['Close']
        ma_fast = latest['MA_Fast']
        ma_slow = latest['MA_Slow']
        
        # 현재 보유 상태 및 수익률 체크
        holding_info = None
        for h in current_holdings:
            if h.get('pdno') == target_code:
                holding_info = h
                break

        # [SELL 시그널 체크 - 보유 중일 때만]
        if holding_info:
            profit_pct = float(holding_info.get('evlu_pfls_rt', 0.0))
            
            # 1. 손절 조건 최우선
            if profit_pct <= self.stop_loss_pct:
                return "SELL", f"Stop Loss Reached ({profit_pct:.2f}% <= {self.stop_loss_pct}%)", 0.0
                
            # 2. 익절 조건 (간단한 고정 익절)
            if profit_pct >= self.take_profit_pct:
                 return "SELL", f"Take Profit Reached ({profit_pct:.2f}% >= {self.take_profit_pct}%)", 0.0
                 
            # 3. 추세 이탈 손절 (20일선 붕괴)
            if price < ma_slow and prev['Close'] >= prev['MA_Slow']:
                return "SELL", f"Trend Breakdown (Price < {self.ma_slow_period} MA)", 0.0
                 
            return "HOLD", f"Holding (Profit: {profit_pct:.2f}%)", 0.0

        # [BUY 시그널 체크 - 미보유 중일 때]
        # 조건: 현재 가격이 느린 이평선 (20일선) 위에 있고, 빠른 이평선 지지받으며 반등 혹은 돌파 중
        if price > ma_slow and latest['Volume'] > df['Volume'].rolling(window=20).mean().iloc[-1] * 1.5:
            # 단순 예시: 20일선 위에 있고, 당일 거래량이 20일 평균의 1.5배 이상 터짐
            # 목표 비중 0.05 (자산의 5% 진입)
            target_peso = 0.05
            return "BUY", f"Trend Breakout with Volume (Price > {self.ma_slow_period} MA)", target_peso

        return "HOLD", f"No Signal (Price: {price:,.0f})", 0.0
