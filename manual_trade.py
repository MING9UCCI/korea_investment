import logging
import config
from kis_api import KisApi

# Setup Logging
logging.basicConfig(level=logging.INFO)

def main():
    print("🚀 Starting Manual Trade Test: Samsung SDI (006400)")
    
    # Initialize API
    kis = KisApi()
    
    # Target: Samsung SDI
    stock_code = "006400"
    qty = 1 # Buy 1 share
    
    # 1. Check Current Price
    print(f"🔍 Checking price for {stock_code}...")
    price_data = kis.get_current_price(stock_code)
    
    if not price_data:
        print("❌ Failed to get current price. KIS API might be unstable (500 Error).")
        return

    current_price = int(price_data['output']['stck_prpr'])
    print(f"💰 Current Price: {current_price} KRW")
    
    # 2. Execute Buy Order
    print(f"🛒 Attempting to BUY {qty} share(s)...")
    result = kis.buy_order(stock_code, qty)
    
    print("✅ Trade Result:", result)

if __name__ == "__main__":
    main()
