import logging
from core.kis_client import KisClient
from config.config_manager import config_manager
from core.logger import db_logger, get_logger

logger = get_logger("order_executor")

class OrderExecutor:
    def __init__(self, kis_client: KisClient):
        self.kis = kis_client
        self.is_real = config_manager.is_real_mode
        self.cano = config_manager.kis_creds.get('cano')
        self.acnt_prdt_cd = config_manager.kis_creds.get('acnt_prdt_cd', '01')

    def check_balance(self):
        path = "uapi/domestic-stock/v1/trading/inquire-balance"
        tr_id = "TTTC8434R" if self.is_real else "VTTC8434R"
        headers = self.kis.get_headers(tr_id)
        
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "01", 
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK": "",
            "CTX_AREA_NK": ""
        }
        
        res = self.kis._request('GET', path, headers=headers, params=params)
        if res and res.get('rt_cd') == '0':
            holdings = res.get('output1', [])
            summary = res.get('output2', [{}])[0]
            # output2 에는 총 자산 등의 요약 정보가 있음.
            # tot_evlu_amt (총 평가 금액)
            return holdings, summary
        return [], {}

    def get_available_cash(self):
        """매수 가능한 최대 예수금을 조회 (단순화)"""
        _, summary = self.check_balance()
        if summary:
            return int(summary.get('dnca_tot_amt', 0)) # 예수금 총계
            # 혹은 실 매수 가능 금액 (prvs_rcdl_excc_amt 등) API 응답 템플릿에 따라 선택
        return 0
        
    def get_total_asset(self):
        _, summary = self.check_balance()
        if summary:
             return int(summary.get('tot_evlu_amt', 0))
        return 0

    def place_order(self, code, qty, is_buy=True, price=0):
        """
        주문 실행. price=0이면 시장가 주문 (01).
        """
        path = "uapi/domestic-stock/v1/trading/order-cash"
        
        if is_buy:
             tr_id = "TTTC0802U" if self.is_real else "VTTC0802U"
        else:
             tr_id = "TTTC0801U" if self.is_real else "VTTC0801U"

        headers = self.kis.get_headers(tr_id)
        
        # 01: 시장가, 00: 지정가
        ord_dvsn = "01" if price == 0 else "00"
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": code,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price)
        }
        
        res = self.kis._request('POST', path, headers=headers, data=body)
        if res and res.get('rt_cd') == '0':
            order_no = res.get('output', {}).get('ODNO', 'Unknown')
            action_type = "BUY" if is_buy else "SELL"
            logger.info(f"{action_type} Order Success. No: {order_no}, Code: {code}, Qty: {qty}")
            return True, order_no
        else:
            msg = res.get('msg1') if res else 'Unknown API Error'
            action_type = "BUY" if is_buy else "SELL"
            logger.error(f"{action_type} Order Failed: Code: {code}, Qty: {qty}. Msg: {msg}")
            return False, msg
