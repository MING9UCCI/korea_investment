import requests
import json
import time
import pandas as pd
from datetime import datetime
import config

class KisApi:
    def __init__(self):
        self.app_key = config.APP_KEY
        self.app_secret = config.APP_SECRET
        self.url_base = config.URL_BASE
        
        # Debug Log for Account ID (Masked)
        masked_cano = config.CANO[:4] + "****" if config.CANO and len(config.CANO) > 4 else "INVALID"
        print(f"[KisApi] Initializing. Mode: {config.KIS_MODE} | CANO: {masked_cano} | URL: {self.url_base}")
        
        self.access_token = None
        self.token_file = "token.json"
        self._load_token()

    def _load_token(self):
        """Load token from file or issue a new one if expired."""
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                # Check expiration (simplified check, real usage should parse expiration)
                self.access_token = token_data.get('access_token')
                print("Loaded existing token.")
        except FileNotFoundError:
            print("No token file found. Issuing new token...")
            self._issue_token()

    def _issue_token(self):
        """Issue a new access token from KIS API."""
        path = "oauth2/tokenP"
        url = f"{self.url_base}/{path}"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            data = res.json()
            self.access_token = data['access_token']
            
            # Save token
            with open(self.token_file, 'w') as f:
                json.dump(data, f)
            print("New token issued and saved.")
        except Exception as e:
            print(f"Failed to issue token: {e}")
            # Ensure we don't crash hard if simple init fails, but logging is crucial
    
    def _get_headers(self, tr_id):
        """Construct headers for API requests."""
        if not self.access_token:
            self._issue_token()
            
        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }

    def get_current_price(self, code):
        """Fetch current price for a given stock code."""
        path = "uapi/domestic-stock/v1/quotations/inquire-price"
        url = f"{self.url_base}/{path}"
        headers = self._get_headers("FHKST01010100")
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                return {
                    "code": code,
                    "price": int(data['output']['stck_prpr']),
                    "name": data['output'].get('rprs_mrkt_kor_name', code) # Might not be available in all responses
                }
            else:
                print(f"Error getting price for {code}: {data['msg1']}")
                return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error in get_current_price for {code}: {e}")
            print(f"Response status: {e.response.status_code}")
            if e.response.status_code == 500:
                print("⚠️  KIS API Server Error (500) - This is a server-side issue, not a code problem")
            return None
        except Exception as e:
            print(f"Exception in get_current_price: {e}")
            return None

    def get_market_price_history(self, code, period="D"):
        """Fetch daily OHLCV data for technical analysis.
        NOTE: KIS API specific logic for history might differ.
        Using 'inquire-daily-itemchartprice' or similar.
        """
        path = "uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
        url = f"{self.url_base}/{path}"
        headers = self._get_headers("FHKST03010100")
        
        # Simple date range: last 30 days roughly
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - pd.Timedelta(days=100)).strftime("%Y%m%d")
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code,
            "fid_input_date_1": start_date,
            "fid_input_date_2": end_date,
            "fid_period_div_code": period, # D: Day, W: Week, M: Month
            "fid_org_adj_prc": "1" # Adjusted price
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                items = data['output2']
                df = pd.DataFrame(items)
                # Rename columns for convenience
                # stck_bsop_date: Date, stck_clpr: Close, stck_oprc: Open, stck_hgpr: High, stck_lwpr: Low, acml_vol: Volume
                df = df.rename(columns={
                    "stck_bsop_date": "Date",
                    "stck_clpr": "Close",
                    "stck_oprc": "Open",
                    "stck_hgpr": "High",
                    "stck_lwpr": "Low",
                    "acml_vol": "Volume"
                })
                # Convert types
                cols = ["Close", "Open", "High", "Low", "Volume"]
                df[cols] = df[cols].astype(float)
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date').reset_index(drop=True)
                return df
            else:
                print(f"Error getting history for {code}: {data['msg1']}")
                return pd.DataFrame()
        except Exception as e:
            print(f"Exception in get_market_price_history: {e}")
            return pd.DataFrame()

    def get_volume_rank(self, limit=100):
        """Fetch top stocks by trading volume."""
        path = "uapi/domestic-stock/v1/quotations/volume-rank"
        url = f"{self.url_base}/{path}"
        headers = self._get_headers("FHPST01710000")
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J", # J: Stock Market, W: KOSDAQ (Need to support both or selectable?)
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": "0000", # All
            "FID_DIV_CLS_CODE": "0", # 0: Volume, 1: Amount
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111", # Filter ETF/ETN etc? 1 means exclude. 
            # 1: Investment Trust, 2: ETF, 3: ETN, etc. 
            # Let's keep it simple for now or strictly Stocks.
            # "0" includes everything.
            "FID_TRGT_EXCLS_CLS_CODE": "0", 
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": ""
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                items = data['output']
                # Return list of codes
                codes = [item['mksc_shrn_iscd'] for item in items[:limit]]
                return codes
            else:
                print(f"Volume Rank Failed: {data['msg1']}")
                return []
        except Exception as e:
            print(f"Exception in get_volume_rank: {e}")
            return []

    def buy_order(self, code, qty):
        """Execute a market buy order."""
        path = "uapi/domestic-stock/v1/trading/order-cash"
        url = f"{self.url_base}/{path}"
        # TTTC0802U: Buy (Virtual), TTTC0802U needs checking for Real vs Virtual?
        # Actually, for real it's usually TTTC0802U (Stock Buy)
        # But allow switching based on config.
        # This is simplified. Real implementation needs rigorous TR ID checking.
        tr_id = "TTTC0802U" if config.MODE == "REAL" else "VTTC0802U"
        
        headers = self._get_headers(tr_id)
        body = {
            "CANO": config.CANO,
            "ACNT_PRDT_CD": config.ACNT_PRDT_CD,
            "PDNO": code,
            "ORD_DVSN": "01", # 01: Market Price
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0" # 0 for market price
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                print(f"Active Buy Order: {code}, Qty: {qty}")
                return True
            else:
                print(f"Buy Order Failed: {data['msg1']}")
                return False
        except Exception as e:
            print(f"Exception in buy_order: {e}")
            return False

    def sell_order(self, code, qty):
        """Execute a market sell order."""
        path = "uapi/domestic-stock/v1/trading/order-cash"
        url = f"{self.url_base}/{path}"
        # TTTC0801U: Sell (Real), VTTC0801U: Sell (Virtual)
        tr_id = "TTTC0801U" if config.KIS_MODE == "REAL" else "VTTC0801U"
        
        headers = self._get_headers(tr_id)
        body = {
            "CANO": config.CANO,
            "ACNT_PRDT_CD": config.ACNT_PRDT_CD,
            "PDNO": code,
            "ORD_DVSN": "01", # 01: Market Price
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0" # 0 for market price
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                print(f"Active Sell Order: {code}, Qty: {qty}")
                return True
            else:
                print(f"Sell Order Failed: {data['msg1']}")
                return False
        except Exception as e:
            print(f"Exception in sell_order: {e}")
            return False

    def get_overseas_holdings(self):
        """Fetch overseas stock holdings."""
        # Note: Virtual trading for overseas stocks might be limited or use different TR IDs.
        # This implementation assumes standard KIS API structure for overseas balance.
        path = "uapi/overseas-stock/v1/trading/inquire-balance"
        url = f"{self.url_base}/{path}"
        
        # TR ID for Overseas Balance: VTTS3012R (Virtual), TTTS3012R (Real)
        # Verify this TR ID from documentation if possible. 
        tr_id = "TTTS3012R" if config.KIS_MODE == "REAL" else "VTTS3012R"
        
        headers = self._get_headers(tr_id)
        
        # Overseas params are slightly different
        params = {
            "CANO": config.CANO,
            "ACNT_PRDT_CD": config.ACNT_PRDT_CD,
            "OVRS_EXCG_CD": "NASD", # NASD (Nasdaq), NYSE (New York), AMS (Amex), etc. or try to get all?
            # KIS API often requires specific exchange code. 
            # Let's try "NASD" as default for US stocks.
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK": "",
            "CTX_AREA_NK": ""
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
             # Don't raise for status immediately, check rt_cd first if possible, 
             # but standard is raise then check json.
            if res.status_code != 200:
                 # If 500 or 404, just return empty list and log warning
                print(f"Warning: Overseas holdings check failed with status {res.status_code}")
                return []
                
            data = res.json()
            if data['rt_cd'] == '0':
                return data['output1'] # output1 usually contains holdings list
            else:
                print(f"Overseas Balance Check Failed: {data['msg1']} (Code: {data['msg_cd']})")
                return []
        except Exception as e:
            print(f"Exception in get_overseas_holdings: {e}")
            return []

    def check_balance(self):
        """Check account balance."""
        path = "uapi/domestic-stock/v1/trading/inquire-balance"
        url = f"{self.url_base}/{path}"
        tr_id = "TTTC8434R" if config.MODE == "REAL" else "VTTC8434R"
        
        headers = self._get_headers(tr_id)
        params = {
            "CANO": config.CANO,
            "ACNT_PRDT_CD": config.ACNT_PRDT_CD,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK": "",
            "CTX_AREA_NK": ""
        }
        # Validate Account Config
        if not config.CANO or len(config.CANO) != 8:
            print(f"ERROR: Invalid Account Number (CANO): {config.CANO}")
            return [], {}
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                # Return list of holdings and total evaluation
                holdings = data.get('output1', [])
                summary = data.get('output2', [{}])[0]
                return holdings, summary
            else:
                print(f"Balance Check Failed: {data['msg1']}")
                return [], {}
        except Exception as e:
            print(f"Exception in check_balance: {e}")
            return [], {}

    # --- Overseas (US) Methods ---
    
    def get_overseas_price(self, code, excd="NAS"):
        """Fetch current price for US stock."""
        path = "uapi/overseas-price/v1/quotations/price"
        url = f"{self.url_base}/{path}"
        headers = self._get_headers("HHDFS00000300")
        
        params = {
            "AUTH": "",
            "EXCD": excd, # NAS: Nasdaq, NYS: NYSE, AMS: Amex
            "SYMB": code
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                return {
                    "code": code,
                    "price": float(data['output']['last']), # US price is decimal
                    "name": code # Output might not have name
                }
            else:
                print(f"Error getting US price for {code}: {data['msg1']}")
                return None
        except Exception as e:
            print(f"Exception in get_overseas_price: {e}")
            return None

    def get_overseas_history(self, code, excd="NAS"):
        """Fetch daily OHLCV for US stock."""
        path = "uapi/overseas-price/v1/quotations/dailyprice"
        url = f"{self.url_base}/{path}"
        headers = self._get_headers("HHDFS76240000")
        
        end_date = datetime.now().strftime("%Y%m%d")
        
        params = {
            "AUTH": "",
            "EXCD": excd,
            "SYMB": code,
            "GUBN": "0", # 0: Daily, 1: Weekly, 2: Monthly
            "BYMD": end_date,
            "MODP": "1" # 1: Modified price
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                items = data['output2']
                df = pd.DataFrame(items)
                # kymd: Date, clos: Close, open: Open, high: High, low: Low, volu: Volume
                df = df.rename(columns={
                    "xymd": "Date", # Note: Field name might be xymd or kymd depending on API version, usually xymd for overseas
                    "clos": "Close",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "tvol": "Volume"
                })
                # Check if xymd exists, sometimes it's distinct
                if 'Date' not in df.columns and 'kymd' in df.columns:
                     df = df.rename(columns={'kymd': 'Date'})

                cols = ["Close", "Open", "High", "Low", "Volume"]
                df[cols] = df[cols].astype(float)
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date').reset_index(drop=True)
                return df
            else:
                print(f"Error getting US history for {code}: {data['msg1']}")
                return pd.DataFrame()
        except Exception as e:
            print(f"Exception in get_overseas_history: {e}")
            return pd.DataFrame()

    def buy_overseas_order(self, code, qty, excd="NAS"):
        """Execute US Buy Order."""
        path = "uapi/overseas-stock/v1/trading/order"
        url = f"{self.url_base}/{path}"
        # Real: JTTT1002U (Buy), Virtual: VTTT1002U (Buy)
        # Note: Check API docs. Usually JTTT1002U (NAS Buy) / JTTT1006U (NYS Buy) ??
        # Or simplified integrated TR? 
        # Using VTTT1002U for virtual (common for all).
        # Real might differ by exchange. Let's assume JTTT1002U (USA Buy).
        
        tr_id = "JTTT1002U" if config.MODE == "REAL" else "VTTT1002U"
        
        headers = self._get_headers(tr_id)
        body = {
            "CANO": config.CANO,
            "ACNT_PRDT_CD": config.ACNT_PRDT_CD,
            "OVRS_EXCG_CD": excd,
            "PDNO": code,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": "0", # Market price (if allowed)? US usually requires Limit?
            # Warning: US Market Order often requires ORD_DVSN="00" and price=0?
            # KIS Guide: "00" Limit, "34" Market ?? 
            # Let's try Market Price "00" (Limit) with Price 0? No, that fails.
            # US Market Order is restricted in KIS API usually. 
            # Better to fetch current price -> add buffer -> Send Limit Order.
            # For simplicity here, let's try setting price to 0 and "34" (Market)?
            # Or just warn user.
            "ORD_SVR_DVSN_CD": "0", 
            "ORD_DVSN": "00" # Limit Order default
        }
        
        # Calculate Limit Price (Current + 1% for Buy)
        curr = self.get_overseas_price(code, excd)
        if curr:
            price = curr['price']
            limit_price = price * 1.02 # Buy 2% higher to ensure execution
            body["OVRS_ORD_UNPR"] = str(round(limit_price, 2))
        else:
            print("Cannot fetch price for limit order.")
            return False

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                print(f"Active US Buy Order: {code}, Qty: {qty}, Price: {body['OVRS_ORD_UNPR']}")
                return True
            else:
                print(f"US Buy Order Failed: {data['msg1']}")
                return False
        except Exception as e:
            print(f"Exception in buy_overseas_order: {e}")
            return False

    def sell_overseas_order(self, code, qty, excd="NAS"):
        """Execute US Sell Order."""
        path = "uapi/overseas-stock/v1/trading/order"
        url = f"{self.url_base}/{path}"
        # Real: JTTT1006U (Sell)? VTTT1001U?
        # Virtual: VTTT1006U (Sell)
        
        tr_id = "JTTT1006U" if config.MODE == "REAL" else "VTTT1006U"
        
        headers = self._get_headers(tr_id)
        body = {
            "CANO": config.CANO,
            "ACNT_PRDT_CD": config.ACNT_PRDT_CD,
            "OVRS_EXCG_CD": excd,
            "PDNO": code,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": "0",
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        
        # Calculate Limit Price (Current - 1% for Sell)
        curr = self.get_overseas_price(code, excd)
        if curr:
            price = curr['price']
            limit_price = price * 0.98
            body["OVRS_ORD_UNPR"] = str(round(limit_price, 2))
        else:
            return False

        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            data = res.json()
            if data['rt_cd'] == '0':
                print(f"Active US Sell Order: {code}, Qty: {qty}")
                return True
            else:
                print(f"US Sell Order Failed: {data['msg1']}")
                return False
        except Exception as e:
            print(f"Exception in sell_overseas_order: {e}")
            return False
