import pandas as pd
from datetime import datetime
from core.kis_client import KisClient
from core.logger import get_logger

logger = get_logger("data_feed")

class DataFeed:
    def __init__(self, kis_client: KisClient):
        self.kis = kis_client

    def get_current_price(self, code):
        path = "uapi/domestic-stock/v1/quotations/inquire-price"
        headers = self.kis.get_headers("FHKST01010100")
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code
        }
        res = self.kis._request('GET', path, headers=headers, params=params)
        if res and res.get('rt_cd') == '0':
            return {
                "code": code,
                "price": int(res['output']['stck_prpr']),
                "name": res['output'].get('rprs_mrkt_kor_name', code)
            }
        return None

    def get_daily_history(self, code, lookback_days=100):
        path = "uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        headers = self.kis.get_headers("FHKST03010100")
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=lookback_days)
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code,
            "fid_input_date_1": start_date.strftime("%Y%m%d"),
            "fid_input_date_2": end_date.strftime("%Y%m%d"),
            "fid_period_div_code": "D",
            "fid_org_adj_prc": "1" # 수정주가 반영
        }
        
        res = self.kis._request('GET', path, headers=headers, params=params)
        if res and res.get('rt_cd') == '0':
            items = res.get('output2', [])
            if not items:
                return pd.DataFrame()
            
            df = pd.DataFrame(items)
            df = df.rename(columns={
                "stck_bsop_date": "Date",
                "stck_clpr": "Close",
                "stck_oprc": "Open",
                "stck_hgpr": "High",
                "stck_lwpr": "Low",
                "acml_vol": "Volume"
            })
            cols = ["Close", "Open", "High", "Low", "Volume"]
            df[cols] = df[cols].astype(float)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date').reset_index(drop=True)
            return df
        return pd.DataFrame()

    def get_volume_rank(self, limit=50):
        """특정 거래량 이상 종목 스캔 (초기 필터링용)"""
        path = "uapi/domestic-stock/v1/quotations/volume-rank"
        headers = self.kis.get_headers("FHPST01710000")
        params = {
            "FID_COND_MRKT_DIV_CODE": "J", 
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0", 
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111", # ETF/ETN 제외 (순수 주식만)
            "FID_TRGT_EXCLS_CLS_CODE": "0", 
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": ""
        }
        
        res = self.kis._request('GET', path, headers=headers, params=params)
        if res and res.get('rt_cd') == '0':
            items = res.get('output', [])
            return [item['mksc_shrn_iscd'] for item in items[:limit]]
        return []
