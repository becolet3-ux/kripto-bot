import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from src.execution.executor import BinanceExecutor
from src.utils.exceptions import InsufficientBalanceError

class TestExecutor(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Mock settings
        self.settings_patcher = patch('src.execution.executor.settings')
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.LIVE_TRADING = False
        self.mock_settings.TRADING_MODE = 'spot'
        self.mock_settings.LEVERAGE = 1
        self.mock_settings.STATE_FILE = 'test_state.json'
        self.mock_settings.STATS_FILE = 'test_stats.json'
        self.mock_settings.MAX_DAILY_LOSS_PCT = 5.0
        self.mock_settings.SNIPER_MAX_RISK_PCT = 98.0
        self.mock_settings.MAX_OPEN_POSITIONS = 3
        self.mock_settings.PAPER_TRADING_BALANCE = 1000.0
        
        # Mock StateManager
        self.state_manager_patcher = patch('src.execution.executor.StateManager')
        self.mock_state_manager_cls = self.state_manager_patcher.start()
        self.mock_state_manager = self.mock_state_manager_cls.return_value
        self.mock_state_manager.load_state.return_value = {}
        self.mock_state_manager.load_stats.return_value = {}

        # Mock Exchange Client
        self.mock_exchange = MagicMock()
        
        # Initialize Executor
        self.executor = BinanceExecutor(exchange_client=self.mock_exchange, is_tr=False)
        # Force live mode for execution logic testing
        self.executor.is_live = True 
        self.executor.exchange_spot = self.mock_exchange

    async def asyncTearDown(self):
        self.settings_patcher.stop()
        self.state_manager_patcher.stop()

    async def test_execute_buy_min_notional_bump(self):
        """Test if quantity is increased when below min notional and balance allows"""
        symbol = "BTC/USDT"
        price = 50000.0
        # Quantity that results in $2.5 value (below default $5.0 min)
        small_qty = 0.00005 # $2.5
        
        # Mock get_symbol_info
        self.executor.get_symbol_info = AsyncMock(return_value={
            'minNotional': '5.0',
            'stepSize': '0.00001',
            'minQty': '0.00001'
        })
        
        # Mock get_free_balance to return plenty
        self.executor.get_free_balance = AsyncMock(return_value=100.0)
        
        # Mock CCXT create_order (via asyncio.to_thread wrapper in code)
        # The code uses asyncio.to_thread(self.exchange_spot.create_order, ...)
        # So we mock exchange_spot.create_order
        self.mock_exchange.create_market_buy_order = MagicMock(return_value={'id': '123', 'status': 'closed'})
        
        # Execute
        # Note: The code snippet I read earlier had the bump logic inside execute_buy for Global/CCXT path.
        # I need to ensure that path is taken.
        
        await self.executor.execute_buy(symbol, small_qty, price)
        
        # Verify
        # The quantity should be bumped to at least $5.0 / 50000 = 0.0001
        # Code typically bumps with 5% buffer -> $5.25 -> 0.000105
        
        self.mock_exchange.create_market_buy_order.assert_called_once()
        call_args = self.mock_exchange.create_market_buy_order.call_args
        # args: symbol, amount (for create_market_buy_order)
        
        # Check amount argument (2nd arg, index 1)
        actual_qty = call_args[0][1]
        
        expected_min_qty = 5.0 / price
        self.assertGreaterEqual(actual_qty, expected_min_qty)
        self.assertAlmostEqual(actual_qty * price, 5.0, delta=0.5) # Allow some precision variance

    async def test_execute_buy_insufficient_balance_for_bump(self):
        """Test if buy is rejected when below min notional and balance is insufficient"""
        symbol = "BTC/USDT"
        price = 50000.0
        small_qty = 0.00005 # $2.5
        
        self.executor.get_symbol_info = AsyncMock(return_value={
            'minNotional': '5.0',
            'stepSize': '0.00001'
        })
        
        # Mock low balance ($3.0 available, need ~$5.25)
        self.executor.get_free_balance = AsyncMock(return_value=3.0)
        
        result = await self.executor.execute_buy(symbol, small_qty, price)
        
        # Should fail
        self.assertFalse(result)
        self.mock_exchange.create_market_buy_order.assert_not_called()

if __name__ == '__main__':
    unittest.main()
