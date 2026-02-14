import os
import tempfile
from config.settings import settings
from src.learning.brain import BotBrain


def test_sl_guard_blocks_after_threshold():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        b = BotBrain(data_file=path)
        settings.STOPLOSS_GUARD_ENABLED = True
        settings.SL_GUARD_WINDOW_MINUTES = 60
        settings.SL_GUARD_MAX_SL_HITS = 2

        b.record_stop_loss_event("BTC/USDT", "ATR_TRAILING_STOP_HIT")
        b.record_stop_loss_event("BTC/USDT", "ATR_TRAILING_STOP_HIT")

        res = b.check_safety("BTC/USDT", current_volatility=0.5, volume_ratio=1.0, current_rsi=50.0)
        assert res["safe"] is False
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def test_sl_guard_allows_under_threshold():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        b = BotBrain(data_file=path)
        settings.STOPLOSS_GUARD_ENABLED = True
        settings.SL_GUARD_WINDOW_MINUTES = 60
        settings.SL_GUARD_MAX_SL_HITS = 3

        b.record_stop_loss_event("ETH/USDT", "ATR_TRAILING_STOP_HIT")
        b.record_stop_loss_event("ETH/USDT", "ATR_TRAILING_STOP_HIT")

        res = b.check_safety("ETH/USDT", current_volatility=0.5, volume_ratio=1.0, current_rsi=50.0)
        assert res["safe"] is True
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
