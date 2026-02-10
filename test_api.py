"""
KIS API Diagnostic Test Script
Tests basic API functionality to identify connection issues
"""
import logging
from kis_api import KisApi
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_token():
    """Test 1: Token issuance"""
    print("\n" + "="*50)
    print("TEST 1: Token Issuance")
    print("="*50)
    
    kis = KisApi()
    if kis.access_token:
        print(f"✅ Token issued successfully: {kis.access_token[:20]}...")
        return kis
    else:
        print("❌ Failed to issue token")
        return None

def test_stock_price(kis):
    """Test 2: Stock price query"""
    print("\n" + "="*50)
    print("TEST 2: Stock Price Query (삼성전자 005930)")
    print("="*50)
    
    try:
        price = kis.get_current_price("005930")
        if price:
            print(f"✅ Current price fetched: {price:,}원")
            return True
        else:
            print("❌ Failed to fetch price (returned None)")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_balance(kis):
    """Test 3: Account balance check"""
    print("\n" + "="*50)
    print("TEST 3: Account Balance Check")
    print("="*50)
    
    try:
        holdings, summary = kis.check_balance()
        print(f"✅ Balance check successful")
        print(f"Holdings: {len(holdings)} items")
        print(f"Summary: {summary}")
        return True
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_overseas_holdings(kis):
    """Test 4: Overseas holdings check"""
    print("\n" + "="*50)
    print("TEST 4: Overseas Holdings Check")
    print("="*50)
    
    try:
        holdings = kis.get_overseas_holdings()
        print(f"✅ Overseas holdings check successful")
        print(f"Holdings: {holdings}")
        return True
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("\n" + "="*50)
    print("KIS API DIAGNOSTIC TEST")
    print(f"Mode: {config.KIS_MODE}")
    print(f"Account: {config.CANO}")
    print("="*50)
    
    # Test 1: Token
    kis = test_token()
    if not kis:
        print("\n❌ CRITICAL: Cannot proceed without token")
        return
    
    # Test 2: Stock Price
    test_stock_price(kis)
    
    # Test 3: Balance
    test_balance(kis)
    
    # Test 4: Overseas Holdings
    test_overseas_holdings(kis)
    
    print("\n" + "="*50)
    print("DIAGNOSTIC TEST COMPLETE")
    print("="*50)

if __name__ == "__main__":
    main()
