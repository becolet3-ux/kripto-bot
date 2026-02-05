import asyncio
import sys
import os
import traceback

# Add the project root to the python path
sys.path.append(os.getcwd())

from src.collectors.binance_loader import BinanceDataLoader

async def main():
    print("Initializing Binance Data Loader...")
    loader = BinanceDataLoader()
    
    try:
        await loader.initialize()
        
        symbol = "BTC/USDT"
        print(f"\nFetching data for {symbol}...")
        
        # Test Price Fetch
        price = await loader.get_current_price(symbol)
        print(f"Current Perp Price: {price}")
        
        # Test Funding Rate
        funding = await loader.get_funding_rate(symbol)
        print(f"Funding Info: {funding}")
        
        # Test Market Structure (Spot vs Perp)
        print("\nAnalyzing Market Structure (Spot vs Perp)...")
        structure = await loader.get_market_structure(symbol)
        
        if structure:
            print(f"Spot Price: {structure['spot_price']}")
            print(f"Perp Price: {structure['perp_price']}")
            print(f"Spread: {structure['spread_pct']:.4%}")
            print(f"Funding Rate: {structure['funding_rate']:.4%}")
        
    except Exception as e:
        print(f"Error Type: {type(e)}")
        print(f"Error Message: {e}")
        traceback.print_exc()
    finally:
        await loader.close()
        print("\nConnection closed.")

if __name__ == "__main__":
    asyncio.run(main())
