import datetime
import holidays
import pytz
import logging

def is_kr_market_open():
    """
    Check if Korean Stock Market is open today (KST).
    Closed on weekends and KR public holidays.
    """
    # 1. Get current time in KST
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.datetime.now(kst)
    today = now_kst.date()
    
    # 2. Check Weekend (0=Mon, 4=Fri, 5=Sat, 6=Sun)
    if today.weekday() >= 5:
        logging.info(f"[Market Schedule] KR Market Closed: Weekend ({today.strftime('%A')})")
        return False
        
    # 3. Check Holidays
    kr_holidays = holidays.KR()
    if today in kr_holidays:
        logging.info(f"[Market Schedule] KR Market Closed: Holiday ({kr_holidays.get(today)})")
        return False
        
    return True

def is_us_market_open():
    """
    Check if US Stock Market is open today (US Eastern Time).
    Closed on weekends and NYSE holidays.
    """
    # 1. Get current time in US Eastern
    est = pytz.timezone('America/New_York')
    now_est = datetime.datetime.now(est)
    today = now_est.date()
    
    # 2. Check Weekend
    if today.weekday() >= 5:
        logging.info(f"[Market Schedule] US Market Closed: Weekend ({today.strftime('%A')})")
        return False
        
    # 3. Check Holidays (using general US holidays as proxy for NYSE)
    us_holidays = holidays.US()
    if today in us_holidays:
        logging.info(f"[Market Schedule] US Market Closed: Holiday ({us_holidays.get(today)})")
        return False
        
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Is KR Market Open?: {is_kr_market_open()}")
    print(f"Is US Market Open?: {is_us_market_open()}")
