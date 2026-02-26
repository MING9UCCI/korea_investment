import pandas as pd
import numpy as np
import logging
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("backtest")

class BacktestEngine:
    def __init__(self, initial_capital=10000000, fee_rate=0.00015, slippage_rate=0.002):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.fee_rate = fee_rate # 증권사 수수료 (예: 0.015%)
        self.slippage_rate = slippage_rate # 슬리피지 (매수/매도 시 불리한 쪽으로 0.2%)
        
        self.positions = {} # {code: {'qty': int, 'avg_price': float}}
        self.trade_log = []
        self.equity_curve = []

    def run(self, data_dict, strategy_name, strategy_params):
        """
        data_dict: {code: pd.DataFrame(OHLCV)}
        """
        logger.info(f"Starting backtest for {strategy_name} with capital: {self.initial_capital:,}")
        
        if strategy_name == 'trend_following':
            strategy = TrendFollowingStrategy(strategy_params)
        elif strategy_name == 'mean_reversion':
             strategy = MeanReversionStrategy(strategy_params)
        else:
            raise ValueError("Unknown strategy")

        # 모든 종목의 날짜를 추출하여 공통 타임라인 생성
        all_dates = set()
        for code, df in data_dict.items():
            if not df.empty and 'Date' in df.columns:
                all_dates.update(df['Date'].tolist())
                
        timeline = sorted(list(all_dates))
        
        for current_idx, current_date in enumerate(timeline):
            daily_total_value = self.capital
            
            # 1. 일자별 데이터 준비 및 시그널 발생
            for code, df in data_dict.items():
                 # 현재 날짜까지의 데이터 슬라이싱
                 history_df = df[df['Date'] <= current_date]
                 if len(history_df) < 20: continue # 전략이 요구하는 최소 데이터 부족 시 패스
                 
                 current_price = history_df.iloc[-1]['Close']
                 
                 # 현재 보유 상태 밈킹 (API 응답 dict 형태와 유사하게)
                 pseudo_holdings = []
                 if code in self.positions:
                     pos = self.positions[code]
                     profit_rt = ((current_price - pos['avg_price']) / pos['avg_price']) * 100
                     pseudo_holdings.append({
                         'pdno': code,
                         'hldg_qty': pos['qty'],
                         'evlu_pfls_rt': profit_rt,
                         'evlu_amt': pos['qty'] * current_price
                     })
                     daily_total_value += pos['qty'] * current_price
                     
                 # 시그널 추출
                 signal, reason, target_peso = strategy.analyze(history_df, pseudo_holdings, code)
                 
                 # 2. 강제 체결 시뮬레이션
                 if signal == "BUY":
                      # 비중 기반 매수 금액 (보유 종목이 없다고 가정하고 잔고 우선순위 배분은 한 번에 1개씩 처리 됨)
                      allocation = self.capital * target_peso
                      if allocation > 0:
                          buy_price = current_price * (1 + self.slippage_rate) # 살 때는 비싸게
                          buy_qty = int(allocation // buy_price)
                          if buy_qty > 0 and self.capital >= (buy_qty * buy_price):
                              cost = buy_qty * buy_price
                              fee = cost * self.fee_rate
                              self.capital -= (cost + fee)
                              
                              if code not in self.positions:
                                  self.positions[code] = {'qty': buy_qty, 'avg_price': buy_price}
                              else: # 물타기
                                  old = self.positions[code]
                                  new_qty = old['qty'] + buy_qty
                                  new_avg = ((old['qty'] * old['avg_price']) + cost) / new_qty
                                  self.positions[code] = {'qty': new_qty, 'avg_price': new_avg}
                                  
                              self.trade_log.append({
                                  'date': current_date, 'code': code, 'type': 'BUY', 
                                  'price': buy_price, 'qty': buy_qty, 'reason': reason
                              })
                              
                 elif signal == "SELL":
                     if code in self.positions:
                         pos = self.positions[code]
                         sell_qty = pos['qty']
                         sell_price = current_price * (1 - self.slippage_rate) # 팔 때는 싸게
                         revenue = sell_qty * sell_price
                         fee = revenue * self.fee_rate
                         tax = revenue * 0.002 # 국내 주식 매도세 0.2%
                         
                         self.capital += (revenue - fee - tax)
                         del self.positions[code]
                         
                         self.trade_log.append({
                              'date': current_date, 'code': code, 'type': 'SELL', 
                              'price': sell_price, 'qty': sell_qty, 'reason': reason
                         })

            # 하루 끝, 자산 가치 기록
            self.equity_curve.append({
                'date': current_date,
                'equity': daily_total_value
            })

    def print_report(self):
        if not self.equity_curve:
            logger.info("No trades executed.")
            return

        df_equity = pd.DataFrame(self.equity_curve)
        df_equity.set_index('date', inplace=True)
        
        final_equity = df_equity['equity'].iloc[-1]
        net_profit = final_equity - self.initial_capital
        return_pct = (net_profit / self.initial_capital) * 100
        
        # MDD 계산
        roll_max = df_equity['equity'].cummax()
        drawdown = df_equity['equity'] / roll_max - 1.0
        mdd = drawdown.min() * 100
        
        logger.info("-" * 40)
        logger.info("=== BACKTEST REPORT ===")
        logger.info(f"Initial Capital   : {self.initial_capital:,.0f} KRW")
        logger.info(f"Final Equity      : {final_equity:,.0f} KRW")
        logger.info(f"Net Profit        : {net_profit:,.0f} KRW")
        logger.info(f"Total Return      : {return_pct:.2f}%")
        logger.info(f"Max Drawdown (MDD): {mdd:.2f}%")
        logger.info(f"Total Trades      : {len(self.trade_log)}")
        logger.info("-" * 40)

# 테스트용 로직
if __name__ == "__main__":
    from core.kis_client import KisClient
    from core.data_feed import DataFeed
    
    logger.info("Fetching sample data for backtesting...")
    kis = KisClient()
    feed = DataFeed(kis)
    
    # 삼성전자, SK하이닉스 샘플 추출
    codes = ["005930", "000660"]
    data_dict = {}
    for c in codes:
        df = feed.get_daily_history(c, lookback_days=300)
        if not df.empty:
            data_dict[c] = df
            
    engine = BacktestEngine(initial_capital=10000000)
    params = {'ma_fast': 5, 'ma_slow': 20, 'take_profit_pct': 10.0, 'stop_loss_pct': -3.0}
    engine.run(data_dict, 'trend_following', params)
    engine.print_report()
