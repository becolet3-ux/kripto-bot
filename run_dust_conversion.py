import asyncio
import os
import sys
from src.execution.executor import BinanceExecutor
from src.collectors.binance_loader import BinanceDataLoader
from config.settings import settings

async def main():
    print("🚀 Starting Dust-to-BNB Conversion Tool...")
    
    # Initialize Loader to get Exchange
    loader = BinanceDataLoader()
    await loader.initialize()
    
    if loader.mock:
        print("❌ Cannot run in Mock Mode. Connect to real API.")
        return

    # Initialize Executor (TR desteği kaldırıldı)
    executor = BinanceExecutor(exchange_client=loader.exchange)
    
    # Run Conversion
    await executor.convert_dust_to_bnb()
    
    print("🏁 Done.")

if __name__ == "__main__":
    asyncio.run(main())
