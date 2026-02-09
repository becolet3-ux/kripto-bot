
import asyncio
import os
import sys
from dotenv import load_dotenv
import ccxt.async_support as ccxt

# Load environment variables
load_dotenv()

API_KEY = os.getenv("BINANCE_GLOBAL_API_KEY")
API_SECRET = os.getenv("BINANCE_GLOBAL_API_SECRET")

async def main():
    if not API_KEY or not API_SECRET:
        print("Error: API keys not found.")
        return

    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'options': {'defaultType': 'spot'}
    })

    try:
        print("Connecting to Binance Global...")
        await exchange.load_markets()
        
        # 1. Check Balances (to see LD assets)
        print("\n--- Checking Spot Balances (for LD assets) ---")
        balance = await exchange.fetch_balance()
        total = balance.get('total', {})
        for asset, amount in total.items():
            if amount > 0 and (asset.startswith('LD') or asset in ['BNB', 'USDT', 'WIF', 'AVAX']):
                print(f"Asset: {asset}, Amount: {amount}")

        # 2. Check Flexible Earn Positions (SAPI)
        print("\n--- Checking Flexible Earn Positions ---")
        try:
            # SAPI endpoint: GET /sapi/v1/simple-earn/flexible/position
            # CCXT method: sapi_get_simple_earn_flexible_position
            positions = await exchange.sapi_get_simple_earn_flexible_position({'size': 100})
            
            if isinstance(positions, dict) and 'rows' in positions:
                rows = positions['rows']
            else:
                rows = positions

            print(f"Found {len(rows)} Earn positions.")
            for pos in rows:
                asset = pos.get('asset')
                amount = pos.get('totalAmount')
                product_id = pos.get('productId')
                print(f"Earn Position: {asset} | Amount: {amount} | ProductID: {product_id}")

        except Exception as e:
            print(f"Error fetching Earn positions: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
