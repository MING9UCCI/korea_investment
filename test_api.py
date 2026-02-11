import logging
import config
from kis_api import KisApi
import sys

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def main():
    print("🚀 Starting KIS API Test...")
    
    try:
        # 1. Initialize API (Auth)
        print("\n[1] Initializing API & Authentication")
        kis = KisApi()
        print(f"✅ API Initialized (Mode: {config.KIS_MODE})")
        
        # 2. Check Balance
        print("\n[2] Checking Account Balance")
        holdings, balance = kis.check_balance()
        print(f"✅ Balance Check Success")
        print(f"   - Total Eval: {balance.get('tot_evlu_amt', '0')} KRW")
        print(f"   - Holdings Count: {len(holdings)}")
        
        # 3. Check Current Price (Samsung Electronics)
        target_code = "005930" # Samsung Elec
        print(f"\n[3] Checking Price for {target_code}")
        price_info = kis.get_current_price(target_code)
        if price_info:
            print(f"✅ Price Check Success: {price_info['price']} KRW")
        else:
            print("❌ Price Check Failed")
            
        print("\n🎉 Test Completed Successfully!")
        
    except Exception as e:
        print(f"\n❌ Test Failed with Exception: {e}")
        logging.exception("Test failed")

if __name__ == "__main__":
    main()
