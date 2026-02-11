import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.execution.trade_manager import TradeManager
from src.strategies.analyzer import TradeSignal
from src.utils.exceptions import InsufficientBalanceError, ExchangeError

class TestTradeManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.loader = AsyncMock()
        self.analyzer = MagicMock()
        self.executor = AsyncMock()
        # Mock executor attributes
        self.executor.brain = MagicMock()
        self.executor.paper_positions = {}
        
        self.opportunity_manager = MagicMock()
        self.grid_trader = AsyncMock()
        self.grid_trader.active_grids = {}
        self.sentiment_analyzer = AsyncMock()
        
        self.trade_manager = TradeManager(
            self.loader,
            self.analyzer,
            self.executor,
            self.opportunity_manager,
            self.grid_trader,
            self.sentiment_analyzer
        )

    async def test_process_symbol_logic_insufficient_balance(self):
        # Setup
        symbol = 'BTC/USDT'
        self.loader.get_ohlcv.return_value = [[1, 100, 110, 90, 100, 1000]]
        self.analyzer.analyze_spot.return_value = TradeSignal(
            symbol=symbol, action='ENTRY', score=0.9, direction='LONG', 
            estimated_yield=0.1, timestamp=123, details={}
        )
        self.executor.execute_strategy.side_effect = InsufficientBalanceError("Not enough funds")
        self.executor.brain.check_safety.return_value = {'safe': True}
        self.executor.brain.get_weights.return_value = {}
        self.executor.brain.get_indicator_weights.return_value = {}
        
        with patch.object(self.trade_manager, '_validate_signal', new_callable=AsyncMock) as mock_validate:
             mock_validate.return_value = self.analyzer.analyze_spot.return_value
             
             with patch.object(self.trade_manager, '_check_risk_management', new_callable=AsyncMock) as mock_risk:
                 mock_risk.return_value = None

                 # Act
                 result = await self.trade_manager.process_symbol_logic(
                     symbol, {'trend': 'UP'}, {}, {}
                 )

                 # Assert
                 self.assertIsNone(result) # Should catch exception and return None
                 self.executor.execute_strategy.assert_called_once()

    async def test_handle_sniper_mode_buy_success(self):
        # Setup
        signal = TradeSignal(
            symbol='BTC/USDT', action='ENTRY', score=0.8, direction='LONG', 
            estimated_yield=0.1, timestamp=123, details={}
        )
        self.executor.paper_positions = {} # Empty portfolio
        self.sentiment_analyzer.get_futures_sentiment.return_value = {'long_short_ratio': 1.0}

        # Act
        await self.trade_manager.handle_sniper_mode([signal], {'BTC/USDT': 50000})

        # Assert
        self.executor.execute_strategy.assert_called_once_with(signal)
        self.assertTrue(signal.details['force_all_in'])

    async def test_handle_sniper_mode_buy_failure(self):
        # Setup
        signal = TradeSignal(
            symbol='BTC/USDT', action='ENTRY', score=0.8, direction='LONG', 
            estimated_yield=0.1, timestamp=123, details={}
        )
        self.executor.paper_positions = {} 
        self.executor.execute_strategy.side_effect = ExchangeError("Binance Error")
        self.sentiment_analyzer.get_futures_sentiment.return_value = {'long_short_ratio': 1.0}

        # Act
        # Should not raise exception, just log it
        await self.trade_manager.handle_sniper_mode([signal], {'BTC/USDT': 50000})

        # Assert
        self.executor.execute_strategy.assert_called_once()

    async def test_handle_sniper_mode_swap(self):
        # Setup
        self.executor.paper_positions = {'ETH/USDT': {'quantity': 1, 'entry_price': 2000}}
        current_signal = TradeSignal(symbol='ETH/USDT', action='HOLD', score=2.0, direction='LONG', estimated_yield=0, timestamp=123, details={})
        better_signal = TradeSignal(symbol='BTC/USDT', action='ENTRY', score=8.0, direction='LONG', estimated_yield=0, timestamp=123, details={})
        
        self.sentiment_analyzer.get_futures_sentiment.return_value = {'long_short_ratio': 1.0}
        
        # Act
        # First pass - just increment counter
        await self.trade_manager.handle_sniper_mode([current_signal, better_signal], {'ETH/USDT': 2000, 'BTC/USDT': 50000})
        self.assertEqual(self.trade_manager.swap_confirmation_tracker.get('ETH/USDT'), 1)
        self.executor.execute_strategy.reset_mock()
        
        # Second pass
        await self.trade_manager.handle_sniper_mode([current_signal, better_signal], {'ETH/USDT': 2000, 'BTC/USDT': 50000})
        self.assertEqual(self.trade_manager.swap_confirmation_tracker.get('ETH/USDT'), 2)
        self.executor.execute_strategy.reset_mock()
        
        # Third pass - trigger swap
        await self.trade_manager.handle_sniper_mode([current_signal, better_signal], {'ETH/USDT': 2000, 'BTC/USDT': 50000})
        
        # Assert
        # Check if sell was called (which calls execute_strategy with score -10.0)
        # Verify call args
        self.assertEqual(self.executor.execute_strategy.call_count, 2)
        
        # First call should be sell
        first_call = self.executor.execute_strategy.call_args_list[0]
        signal_arg = first_call[0][0]
        self.assertEqual(signal_arg.symbol, 'ETH/USDT')
        self.assertEqual(signal_arg.action, 'EXIT')
        self.assertEqual(signal_arg.score, -10.0)
        
        # Second call should be buy
        second_call = self.executor.execute_strategy.call_args_list[1]
        signal_arg_2 = second_call[0][0]
        self.assertEqual(signal_arg_2.symbol, 'BTC/USDT')
        self.assertEqual(signal_arg_2.action, 'ENTRY')


if __name__ == '__main__':
    unittest.main()
