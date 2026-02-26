import time
import requests
import json
import logging
import os
from datetime import datetime, timedelta
from config.config_manager import config_manager
from core.logger import db_logger, get_logger

logger = get_logger("kis_client")

class RateLimiter:
    def __init__(self, calls, period):
        self.calls = calls
        self.period = period
        self.timestamps = []

    def wait(self):
        now = datetime.now()
        # 오래된 타임스탬프 제거
        self.timestamps = [t for t in self.timestamps if now - t < timedelta(seconds=self.period)]
        
        if len(self.timestamps) >= self.calls:
            sleep_time = (self.timestamps[0] + timedelta(seconds=self.period) - now).total_seconds()
            if sleep_time > 0:
                logger.debug(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
            # 대기 후 다시 정리
            now = datetime.now()
            self.timestamps = [t for t in self.timestamps if now - t < timedelta(seconds=self.period)]

        self.timestamps.append(datetime.now())

class KisClient:
    def __init__(self):
        self.creds = config_manager.kis_creds
        self.app_key = self.creds.get('app_key')
        self.app_secret = self.creds.get('app_secret')
        self.cano = self.creds.get('cano')
        self.acnt_prdt_cd = self.creds.get('acnt_prdt_cd', '01')
        self.url_base = self.creds.get('url_base')
        self.is_real = config_manager.is_real_mode
        self.access_token = None
        self.token_file = "config/token.json"
        
        # 한국투자증권 일반 API는 초당 20건 제한. 여유를 두고 초당 15건으로 설정.
        self.limiter = RateLimiter(calls=15, period=1.0)
        
        logger.info(f"Initializing KisClient (Mode: {'REAL' if self.is_real else 'VIRTUAL'})")
        self._load_token()

    def _load_token(self):
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    # 만료 시간 체크 로직 추가 권장
                    self.access_token = token_data.get('access_token')
                    logger.info("Loaded existing access token.")
            else:
                self._issue_token()
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            self._issue_token()

    def _issue_token(self):
        path = "oauth2/tokenP"
        url = f"{self.url_base}/{path}"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        try:
            res = requests.post(url, headers=headers, json=body, timeout=5)
            res.raise_for_status()
            data = res.json()
            self.access_token = data.get('access_token')
            
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
            with open(self.token_file, 'w') as f:
                json.dump(data, f)
            logger.info("New access token issued and saved.")
        except Exception as e:
            logger.error(f"Failed to issue token: {e}")
            db_logger.log_error("kis_client", f"Token issue failed: {str(e)}")
            raise

    def get_headers(self, tr_id):
        if not self.access_token:
            self._issue_token()
        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P" # 개인
        }

    def _request(self, method, path, headers=None, params=None, data=None, max_retries=3):
        url = f"{self.url_base}/{path}"
        
        for attempt in range(max_retries):
            self.limiter.wait()
            try:
                res = requests.request(method, url, headers=headers, params=params, json=data, timeout=5)
                # 토큰 만료 시 (대개 4XX 에러나 특정 rt_cd 반환)
                if res.status_code == 401 or (res.status_code == 200 and res.json().get('msg_cd') == 'EGW00123'):
                    logger.warning("Token expired or invalid, re-issuing...")
                    self._issue_token()
                    headers['authorization'] = f"Bearer {self.access_token}"
                    continue # 재시도
                    
                res.raise_for_status()
                json_res = res.json()
                
                if json_res.get('rt_cd') != '0':
                     logger.warning(f"API returned error: {json_res.get('msg1')} (TR: {headers.get('tr_id')})")
                     # 심각한 에러인 경우 예외 발생 또는 처리
                     
                return json_res
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (Attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    db_logger.log_error("kis_client", f"API Request Failed ({path}): {str(e)}")
                    return None
                time.sleep((2 ** attempt)) # 지수적 백오프

        return None
