import ccxt
import asyncio
import os

async def main():
    exchange = ccxt.binance()
    print("Checking 'dust' methods in ccxt.binance:")
    
    methods = [m for m in dir(exchange) if 'dust' in m.lower() or 'dribblet' in m.lower()]
    for m in methods:
        print(f" - {m}")
        
    print("\nChecking 'sapi' methods related to asset:")
    sapi_methods = [m for m in dir(exchange) if 'sapi' in m.lower() and 'asset' in m.lower()]
    # Print first 10 to avoid spam
    for m in sapi_methods[:10]:
        print(f" - {m}")

    await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
