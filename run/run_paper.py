import time
import schedule
import ai_analyst
from config.config_manager import config_manager
from core.kis_client import KisClient
from core.data_feed import DataFeed
from core.order_executor import OrderExecutor
from risk.risk_manager import RiskManager
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from core.logger import db_logger, get_logger
import warnings

# Disable pandas warnings for cleaner logs
warnings.filterwarnings("ignore")

logger = get_logger("runner_paper")

class PaperTrader:
    def __init__(self):
        if config_manager.is_real_mode:
            logger.critical("API Mode is set to REAL. This script is for PAPER trading only. Aborting.")
            exit(1)
            
        logger.info("Initializing Paper Trader...")
        self.kis = KisClient()
        self.data_feed = DataFeed(self.kis)
        self.executor = OrderExecutor(self.kis)
        self.risk_manager = RiskManager()
        
        # 전략 세팅
        self.strategies = []
        if config_manager.trading_config.get('strategies', {}).get('trend_following', {}).get('active'):
            params = config_manager.get_strategy_params('trend_following').get('params', {})
            self.strategies.append(TrendFollowingStrategy(params))
            logger.info("Strategy Loaded: TrendFollowing")
            
        if config_manager.trading_config.get('strategies', {}).get('mean_reversion', {}).get('active'):
            params = config_manager.get_strategy_params('mean_reversion').get('params', {})
            self.strategies.append(MeanReversionStrategy(params))
            logger.info("Strategy Loaded: MeanReversion")

        # 유니버스 설정
        self.use_scan = config_manager.system_config.get('use_market_scan', False)
        self.universe = config_manager.trading_config.get('universe', {}).get('fixed_targets', [])
        
    def execute_cycle(self):
        logger.info("--- Starting Trading Cycle ---")
        holdings, summary = self.executor.check_balance()
        total_asset = int(summary.get('tot_evlu_amt', 0)) if summary else 0
        
        self.risk_manager.initialize_daily_asset(total_asset)
        self.risk_manager.update_current_asset(total_asset)
        
        if self.use_scan:
            limit = config_manager.system_config.get('scan_limit', 50)
            self.universe = self.data_feed.get_volume_rank(limit=limit)
            logger.info(f"Target Universe Updated by Volume Scan (N={len(self.universe)})")
            
        for code in self.universe:
            try:
                self._process_symbol(code, holdings, total_asset)
            except Exception as e:
                logger.error(f"Error processing symbol {code}: {e}")
                db_logger.log_error("runner_paper", f"Symbol {code} error: {str(e)}")
            time.sleep(0.5) # API 부하 방지용 딜레이
            
        logger.info("--- Trading Cycle Finished ---")
            
    def _process_symbol(self, code, current_holdings, total_asset):
        df = self.data_feed.get_daily_history(code)
        if df.empty:
            return
            
        current_data = self.data_feed.get_current_price(code)
        if not current_data:
            return
            
        current_price = current_data['price']
        name = current_data['name']
        
        # 가장 높은 우선순위의 시그널 적용 (간단화: 첫 번째로 나오는 BUY/SELL 적용)
        final_signal, final_reason, target_peso = "HOLD", "No Signal", 0.0
        
        for strategy in self.strategies:
            signal, reason, peso = strategy.analyze(df, current_holdings, code)
            
            # 여기서 AI Sentiment 개입 (옵션)
            if signal in ["BUY", "SELL"]:
                ai_score, ai_reason, _ = ai_analyst.analyze_sentiment(name)
                reason += f" | AI: {ai_score} ({ai_reason})"
                
                if signal == "BUY" and ai_score < -30:
                     signal = "HOLD"
                     reason += " (Canceled by AI Veto)"
                
            if signal != "HOLD":
                final_signal = signal
                final_reason = reason
                target_peso = peso
                break # 하나의 전략에서 확실한 시그널이 나오면 중단
                
        # 주문 실행
        if final_signal == "BUY":
            can_buy, req_qty = self.risk_manager.can_open_position(code, current_price, target_peso, current_holdings, total_asset)
            if can_buy and req_qty > 0:
                success, order_no = self.executor.place_order(code, req_qty, is_buy=True)
                if success:
                    db_logger.log_trade("PAPER", "KR", code, name, "BUY", 0.0, final_reason, "Executed", current_price, req_qty)
            else:
                 logger.info(f"[{code}] BUY blocked by Risk Manager or Insufficient Funds.")
                 
        elif final_signal == "SELL":
            # 전략이 SELL을 내렸다면 전량 매도 (기본적으로)
            qty = 0
            for h in current_holdings:
                 if h.get('pdno') == code:
                      qty = int(h.get('hldg_qty', 0))
                      break
            if qty > 0:
                 success, order_no = self.executor.place_order(code, qty, is_buy=False)
                 if success:
                     db_logger.log_trade("PAPER", "KR", code, name, "SELL", 0.0, final_reason, "Executed", current_price, qty)

def job():
    trader = PaperTrader()
    trader.execute_cycle()

if __name__ == "__main__":
    logger.info("Starting Paper Trading Daemon...")
    # 실제로는 장 운영 시간에만 돌게 하려면 market_schedule 등 활용
    # 시연을 위해 즉시 1회 실행 후 10분 배치로 돈다고 가정
    job()
    schedule.every(10).minutes.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)
