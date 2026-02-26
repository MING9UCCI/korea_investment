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

warnings.filterwarnings("ignore")

logger = get_logger("runner_live")

class LiveTrader:
    def __init__(self):
        if not config_manager.is_real_mode:
            logger.critical("API Mode is set to VIRTUAL. This script is for REAL LIVE trading. Aborting.")
            exit(1)
            
        logger.info("Initializing LIVE Trader! WARNING: Real Money will be used.")
        self.kis = KisClient()
        self.data_feed = DataFeed(self.kis)
        self.executor = OrderExecutor(self.kis)
        self.risk_manager = RiskManager()
        
        # 실전용 추가 안전장치: 파라미터를 강제로 보수적으로 덮어씀 (초기 자본의 일부만 운용)
        # config의 max 비중을 반토막 낸다던지 하드코딩된 예시
        self.risk_manager.max_weight_per_stock *= 0.5 
        
        self.strategies = []
        if config_manager.trading_config.get('strategies', {}).get('trend_following', {}).get('active'):
            params = config_manager.get_strategy_params('trend_following').get('params', {})
            self.strategies.append(TrendFollowingStrategy(params))
            
        if config_manager.trading_config.get('strategies', {}).get('mean_reversion', {}).get('active'):
            params = config_manager.get_strategy_params('mean_reversion').get('params', {})
            self.strategies.append(MeanReversionStrategy(params))

        self.use_scan = config_manager.system_config.get('use_market_scan', False)
        self.universe = config_manager.trading_config.get('universe', {}).get('fixed_targets', [])
        
    def execute_cycle(self):
        logger.info("--- Starting LIVE Trading Cycle ---")
        holdings, summary = self.executor.check_balance()
        total_asset = int(summary.get('tot_evlu_amt', 0)) if summary else 0
        
        self.risk_manager.initialize_daily_asset(total_asset)
        self.risk_manager.update_current_asset(total_asset)
        
        if self.use_scan:
            limit = config_manager.system_config.get('scan_limit', 50)
            self.universe = self.data_feed.get_volume_rank(limit=limit)
            
        for code in self.universe:
            try:
                self._process_symbol(code, holdings, total_asset)
            except Exception as e:
                logger.error(f"Error processing symbol {code}: {e}")
                # 실시간 알림 로직 (디스코드 모듈 등 연동) 발송
                db_logger.log_error("runner_live", f"Symbol error {code}: {str(e)}")
            time.sleep(1.0) # 실전은 모의투자보다 더 API 레이트 리밋에 민감하므로 딜레이 증대
            
        logger.info("--- LIVE Trading Cycle Finished ---")
            
    def _process_symbol(self, code, current_holdings, total_asset):
        df = self.data_feed.get_daily_history(code)
        if df.empty: return
            
        current_data = self.data_feed.get_current_price(code)
        if not current_data: return
            
        current_price = current_data['price']
        name = current_data['name']
        
        final_signal, final_reason, target_peso = "HOLD", "", 0.0
        
        for strategy in self.strategies:
            signal, reason, peso = strategy.analyze(df, current_holdings, code)
            
            if signal in ["BUY", "SELL"]:
                ai_score, ai_reason, _ = ai_analyst.analyze_sentiment(name)
                reason += f" | AI: {ai_score} ({ai_reason})"
                
                # 매우 엄격한 실전 AI 차단 로직 (조금이라도 부정적이면 매수 포기)
                if signal == "BUY" and ai_score < 0:
                     signal = "HOLD"
                     reason += " (Blocked by LIVE AI Veto)"
                
            if signal != "HOLD":
                final_signal = signal
                final_reason = reason
                target_peso = peso
                break
                
        if final_signal == "BUY":
            can_buy, req_qty = self.risk_manager.can_open_position(code, current_price, target_peso, current_holdings, total_asset)
            if can_buy and req_qty > 0:
                success, order_no = self.executor.place_order(code, req_qty, is_buy=True)
                if success:
                    db_logger.log_trade("LIVE", "KR", code, name, "BUY", 0.0, final_reason, "Executed", current_price, req_qty)
        elif final_signal == "SELL":
            qty = next((int(h.get('hldg_qty', 0)) for h in current_holdings if h.get('pdno') == code), 0)
            if qty > 0:
                 success, order_no = self.executor.place_order(code, qty, is_buy=False)
                 if success:
                     db_logger.log_trade("LIVE", "KR", code, name, "SELL", 0.0, final_reason, "Executed", current_price, qty)

def job():
    trader = LiveTrader()
    trader.execute_cycle()

if __name__ == "__main__":
    logger.info("Starting LIVE Trading Daemon...")
    job()
    schedule.every(30).minutes.do(job) # 실전은 장중 변동성에 휩쓸리지 않게 사이클을 넉넉히 둘 수도 있음
    
    while True:
        schedule.run_pending()
        time.sleep(1)
