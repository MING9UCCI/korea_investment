import logging
from config.config_manager import config_manager
from core.logger import get_logger

logger = get_logger("risk_manager")

class RiskManager:
    def __init__(self):
        self.risk_cfg = config_manager.risk_limits
        self.max_weight_per_stock = self.risk_cfg.get('max_portfolio_weight_per_stock', 0.10)
        self.max_daily_loss_pct = self.risk_cfg.get('max_daily_loss_pct', -3.0)
        
        # 데몬 구동 동안 메모리에 저장할 당일 상태
        self.daily_start_asset = 0
        self.current_asset = 0
        self.is_trading_blocked_today = False

    def initialize_daily_asset(self, total_asset):
        """장이 시작될 때 혹은 데몬이 최초 켜질 때 당일 시작 자산을 설정"""
        # (실제로는 날짜가 바뀌면 갱신되도록 하려면 데몬 루프에서 관리 필요)
        if self.daily_start_asset == 0:
            self.daily_start_asset = total_asset
        self.current_asset = total_asset
        logger.info(f"Daily Asset Initialized: {self.daily_start_asset:,} KRW")

    def update_current_asset(self, total_asset):
        self.current_asset = total_asset
        self.check_daily_loss_limit()

    def check_daily_loss_limit(self):
        """일간 손실 한도 검사 (-3% 등)"""
        if self.daily_start_asset <= 0:
            return

        profit_pct = ((self.current_asset - self.daily_start_asset) / self.daily_start_asset) * 100
        
        if profit_pct <= self.max_daily_loss_pct:
            if not self.is_trading_blocked_today:
                logger.critical(f"🛑 [RISK ALARM] Daily Loss Limit Reached ({profit_pct:.2f}% <= {self.max_daily_loss_pct}%). BLOCKING NEW TRADES TODAY.")
                self.is_trading_blocked_today = True

    def can_open_position(self, code, current_price, target_peso, current_holdings, total_asset):
        """
        신규 진입 혹은 비중 추가가 가능한지 (리스크 한도) 체크
        """
        if self.is_trading_blocked_today:
            logger.warning(f"Trade blocked by Daily Loss Limit for {code}")
            return False, 0
            
        if total_asset <= 0:
            return False, 0

        # 한 종목당 최대 허용 금액 찾기
        max_allowed_amt = total_asset * self.max_weight_per_stock
        
        # 현재 보유 수량 및 금액 파악
        holding_amt = 0
        for h in current_holdings:
            if h.get('pdno') == code:
                holding_amt = int(h.get('evlu_amt', 0))
                break
                
        # 이미 한도를 채웠거나 넘었으면 불가
        if holding_amt >= max_allowed_amt:
            logger.warning(f"Trade blocked: Max portfolio weight reached for {code} ({holding_amt:,} >= {max_allowed_amt:,})")
            return False, 0
            
        # 추가 매수 가능한 여유 금액
        available_amt_for_stock = max_allowed_amt - holding_amt
        
        # 목표 매입 금액 (시그널에서는 보통 전체 자산기준 x%를 요구하지만, 리스크 한도에 맞춰 깎기)
        desired_amt = total_asset * target_peso
        
        # 실제 매수할 금액은 Min(목표 금액, 남은 한도 금액)
        final_amt = min(desired_amt, available_amt_for_stock)
        
        # 금액을 현재가로 나누어서 수량 계산
        if final_amt < current_price:
             logger.warning(f"Not enough peso allocated to buy at least 1 share of {code}")
             return False, 0
             
        buy_qty = int(final_amt // current_price)
        
        if buy_qty > 0:
            return True, buy_qty
        
        return False, 0
