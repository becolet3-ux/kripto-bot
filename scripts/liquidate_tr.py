
import sys
import os
import time
import math
import logging

# Add project root to path
sys.path.append(os.getcwd())

from src.collectors.binance_tr_client import BinanceTRClient
from config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_step_size(symbol_info):
    for filter in symbol_info.get('filters', []):
        if filter['filterType'] == 'LOT_SIZE':
            return float(filter['stepSize'])
    return 1.0

def adjust_quantity(quantity, step_size):
    if step_size == 0:
        return quantity
    precision = int(round(-math.log10(step_size)))
    # Use floor to avoid exceeding balance
    steps = int(quantity / step_size)
    qty = steps * step_size
    if precision > 0:
        return float(f"{qty:.{precision}f}")
    return int(qty)

def main():
    logger.info("🚀 Starting Liquidation Script for Binance TR...")
    
    client = BinanceTRClient()
    
    # 1. Fetch Balances
    logger.info("📊 Fetching Account Balance...")
    balance_resp = client.fetch_balance()
    
    if not balance_resp.get('free'):
        logger.error("❌ Could not fetch balances or wallet is empty.")
        return

    # 2. Get Exchange Info for Precision
    logger.info("ℹ️ Fetching Exchange Info...")
    exchange_info = client.get_exchange_info()
    if exchange_info.get('code', -1) != 0:
        logger.error("❌ Failed to fetch exchange info.")
        symbols_info = {}
    else:
        symbols_info = {s['symbol']: s for s in exchange_info['data']['symbols']}

    # 3. Sell Assets to TRY
    free_balances = balance_resp['free']
    
    for asset, amount in free_balances.items():
        amount = float(amount)
        if amount <= 0:
            continue
            
        if asset in ['USDT', 'TRY']:
            continue
            
        symbol = f"{asset}_TRY"
        logger.info(f"🔍 Checking {asset} ({amount}) -> {symbol}...")
        
        # Check if symbol exists (Binance TR uses global symbols for info usually, need to check map)
        # BinanceTRClient _normalize_symbol handles _ removal if needed
        # But exchange_info from global API uses "BTCTRY"
        
        global_symbol = f"{asset}TRY"
        if global_symbol not in symbols_info:
            logger.warning(f"⚠️ Symbol {global_symbol} not found in exchange info. Skipping.")
            continue
            
        info = symbols_info[global_symbol]
        step_size = get_step_size(info)
        
        qty_to_sell = adjust_quantity(amount, step_size)
        
        if qty_to_sell <= 0:
            logger.warning(f"⚠️ Quantity too small after adjustment: {qty_to_sell}")
            continue

        # Check estimated value
        try:
            # Use get_ticker_24hr which is available in BinanceTRClient
            ticker_resp = client.get_ticker_24hr(symbol)
            if ticker_resp.get('code') == 0:
                ticker_data = ticker_resp.get('data')
                # If list (global api), take first or match symbol
                if isinstance(ticker_data, list):
                     # Usually returns single obj if symbol param passed
                     if len(ticker_data) > 0:
                         ticker_price = float(ticker_data[0]['lastPrice'])
                     else:
                         ticker_price = 0.0
                elif isinstance(ticker_data, dict):
                    ticker_price = float(ticker_data.get('lastPrice', 0))
                else:
                    ticker_price = 0.0
            else:
                ticker_price = 0.0

            if ticker_price == 0:
                 logger.warning(f"⚠️ Price is 0 for {symbol}. Skipping.")
                 continue
                 
        except Exception as e:
            logger.warning(f"⚠️ Could not get price for {symbol}: {e}. Skipping.")
            continue
            
        value = qty_to_sell * ticker_price
        if value < 20.0:
            logger.info(f"🧹 Skipping Dust: {asset} Value: {value:.2f} TRY (< 20 TRY)")
            continue
            
        logger.info(f"💰 Selling {qty_to_sell} {asset} (~{value:.2f} TRY)...")
        
        # Execute Sell
        # BinanceTRClient.new_order(symbol, side, type, quantity)
        # side: 'SELL', type: 'MARKET'
        resp = client.new_order(symbol=symbol, side='SELL', type='MARKET', quantity=qty_to_sell)
        
        if resp.get('code') == 0:
            logger.info(f"✅ SOLD {asset}: {resp}")
        else:
            logger.error(f"❌ Failed to SELL {asset}: {resp}")
            
        time.sleep(1) # Rate limit safety

    # 4. Buy USDT with TRY
    logger.info("🔄 Checking TRY Balance for USDT Conversion...")
    # Re-fetch balance
    balance_resp = client.fetch_balance()
    try_balance = float(balance_resp['free'].get('TRY', 0))
    
    logger.info(f"💵 Total TRY Balance: {try_balance:.2f} TRY")
    
    if try_balance > 20.0:
        symbol = "USDT_TRY"
        global_symbol = "USDTTRY"
        
        if global_symbol in symbols_info:
            info = symbols_info[global_symbol]
            step_size = get_step_size(info)
            
            # Get Price to calculate quantity
            try:
                ticker_resp = client.get_ticker_24hr(symbol)
                if ticker_resp.get('code') == 0:
                     ticker_data = ticker_resp.get('data')
                     if isinstance(ticker_data, dict):
                         usdt_price = float(ticker_data.get('lastPrice', 0))
                     elif isinstance(ticker_data, list) and len(ticker_data) > 0:
                         usdt_price = float(ticker_data[0].get('lastPrice', 0))
                     else:
                         usdt_price = 0.0
                else:
                     usdt_price = 0.0
                
                if usdt_price == 0:
                     raise Exception("USDT Price is 0")
                     
                logger.info(f"💲 Current USDT Price: {usdt_price:.2f} TRY")
                
                raw_qty = try_balance / usdt_price
                # Leave a tiny bit for fees if needed? Market buy by quantity takes quantity of asset.
                # If we buy quantity, we pay in TRY. 
                # On Binance Spot, MARKET BUY is usually by Quote Amount (quoteOrderQty) if using quote currency.
                # BinanceTR Open API v1 might not support quoteOrderQty easily or wrapper might not.
                # Client wrapper takes 'quantity' which maps to 'quantity' param.
                # If 'quantity' is base asset (USDT), we need to calculate it.
                # Let's reduce raw_qty by 1% to be safe against price moves.
                
                safe_qty = raw_qty * 0.99
                qty_to_buy = adjust_quantity(safe_qty, step_size)
                
                est_cost = qty_to_buy * usdt_price
                if est_cost > try_balance:
                    # Still too high? Reduce more
                    qty_to_buy = adjust_quantity(safe_qty * 0.99, step_size)
                
                logger.info(f"🛒 Buying {qty_to_buy} USDT (~{est_cost:.2f} TRY)...")
                
                resp = client.new_order(symbol=symbol, side='BUY', type='MARKET', quantity=qty_to_buy)
                
                if resp.get('code') == 0:
                    logger.info(f"✅ BOUGHT USDT: {resp}")
                else:
                    logger.error(f"❌ Failed to BUY USDT: {resp}")
                    
            except Exception as e:
                logger.error(f"❌ Error during USDT Buy calculation: {e}")
        else:
            logger.error("❌ USDT_TRY symbol info not found.")
    else:
        logger.info("⚠️ TRY Balance too low for USDT conversion (< 20 TRY).")

    logger.info("🏁 Liquidation Process Completed.")

if __name__ == "__main__":
    main()
