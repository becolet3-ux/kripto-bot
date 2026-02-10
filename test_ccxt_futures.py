import asyncio
import ccxt.async_support as ccxt

async def test_ccxt_futures():
    exchange = ccxt.binance({
        'options': {'defaultType': 'future'}
    })
    try:
        # Open Interest
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"Ticker: {ticker.get('openInterest')}") # Some exchanges provide it here

        # Funding Rate
        funding = await exchange.fetch_funding_rate('BTC/USDT')
        print(f"Funding: {funding}")

        # L/S Ratio (Might need implicit API call)
        # ccxt doesn't always have a unified method for LS Ratio, might need implicit
        # GET /futures/data/globalLongShortAccountRatio
        # exchange.fapiPublicGetFuturesDataGlobalLongShortAccountRatio(...)
        if hasattr(exchange, 'fapiDataGetGlobalLongShortAccountRatio'):
             data = await exchange.fapiDataGetGlobalLongShortAccountRatio({'symbol': 'BTCUSDT', 'period': '5m', 'limit': 1})
             print(f"L/S Ratio: {data}")
        else:
            print("No implicit method found for LS Ratio")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_ccxt_futures())
