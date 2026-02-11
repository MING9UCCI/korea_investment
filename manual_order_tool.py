import sys
import logging
from kis_api import KisApi

# Setup Logging (Suppress overly verbose logs if needed, but keep INFO)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def main():
    kis = KisApi()
    
    code = ""
    qty = 0
    action = ""

    # Check if arguments are provided via command line
    if len(sys.argv) == 4:
        # File usage: python manual_order_tool.py [CODE] [QTY] [BUY/SELL]
        code = sys.argv[1]
        qty = int(sys.argv[2])
        action = sys.argv[3].upper()
    else:
        # Interactive Mode
        print("\n=== 🛠️ Manual Market Order Tool (KIS API) ===")
        print("모든 주문은 '시장가(Market Price)'로 실행됩니다.\n")
        
        code = input("1. 종목코드 (예: 000660): ").strip()
        if not code:
            print("❌ 종목코드를 입력해야 합니다.")
            return
            
        try:
            qty_str = input("2. 수량 (예: 1): ").strip()
            qty = int(qty_str)
        except ValueError:
            print("❌ 수량은 숫자만 입력 가능합니다.")
            return
            
        action = input("3. 매수/매도 (BUY/SELL): ").strip().upper()
        if action not in ["BUY", "SELL"]:
            print("❌ 매수(BUY) 또는 매도(SELL)만 가능합니다.")
            return

    print(f"\n🚀 Executing Order: {action} {qty} share(s) of {code} at MARKET PRICE")
    
    # Check current price for reference (optional but good for user confirmation)
    price_info = kis.get_current_price(code)
    curr_price = "Unknown"
    if price_info:
        curr_price = f"{price_info['price']} KRW"
        print(f"   (Current Price Estimate: {curr_price})")
    
    # Execute
    if action == "BUY":
        result = kis.buy_order(code, qty)
    elif action == "SELL":
        result = kis.sell_order(code, qty)
    
    print("\n" + "="*30)
    if result:
        print(f"✅ 주문 전송 성공! ({action} {code} {qty}주)")
    else:
        print(f"❌ 주문 전송 실패. 로그를 확인하세요.")
    print("="*30 + "\n")
    
    # Show Portfolio
    print_portfolio(kis)

def print_portfolio(kis):
    print("\n📊 Current Portfolio Status")
    holdings, balance = kis.check_balance()
    
    # Total Asset
    total_asset = int(balance.get('tot_evlu_amt', 0))
    print(f"💰 현재 보유 금액 (총 평가액): {total_asset:,} KRW")
    
    print("-" * 60)
    print(f"{'종목명(코드)':<20} | {'보유수량':<10} | {'현재가':<10} | {'수익률':<10}")
    print("-" * 60)
    
    if not holdings:
        print("보유한 주식이 없습니다.")
    else:
        for h in holdings:
            name = h.get('prdt_name', 'Unknown')
            code = h.get('pdno', '')
            qty = int(h.get('hldg_qty', 0))
            price = int(h.get('prpr', 0)) # Current price
            profit = float(h.get('evlu_pfls_rt', 0.0))
            
            # Note: 'Purchase Date' is not available in balance check (aggregated).
            # Showing Profit% instead which is more useful.
            print(f"{name}({code}) | {qty:>8}주 | {price:>8,} | {profit:>7.2f}%")
    print("-" * 60 + "\n")

if __name__ == "__main__":
    main()
