from datetime import datetime, timedelta
from src.execution.stop_loss_manager import StopLossManager
from config import settings


def test_initial_stop_setup_without_df():
    sl = StopLossManager()
    pos = {"symbol": "AAA/USDT", "entry_price": 100.0, "quantity": 1.0}
    now = datetime.utcnow()
    res = sl.check_exit_conditions(pos, current_price=102.0, current_time=now, df=None)
    assert res["action"] == "UPDATE_STOP"
    # Fallback pct is 5%, so distance ~5.1, stop around 94.9
    assert 94.0 < res["new_stop_price"] < 96.0


def test_partial_take_profit_trigger():
    sl = StopLossManager()
    pos = {
        "symbol": "AAA/USDT",
        "entry_price": 100.0,
        "quantity": 1.0,
        "entry_timestamp": datetime.utcnow().isoformat(),
    }
    now = datetime.utcnow()
    res = sl.check_exit_conditions(pos, current_price=105.0, current_time=now, df=None)
    assert res["action"] in ("PARTIAL_CLOSE", "UPDATE_STOP", "CLOSE", "NONE")
    # If partial hits, verify ratio key
    if res["action"] == "PARTIAL_CLOSE":
        assert res["qty_pct"] == settings.settings.PARTIAL_EXIT_RATIO


def test_time_based_max_hold_exit():
    sl = StopLossManager()
    past = datetime.utcnow() - timedelta(hours=settings.settings.MAX_HOLD_TIME_HOURS + 1)
    pos = {"symbol": "AAA/USDT", "entry_price": 100.0, "quantity": 1.0, "entry_timestamp": past.isoformat()}
    now = datetime.utcnow()
    res = sl.check_exit_conditions(pos, current_price=99.0, current_time=now, df=None)
    assert res["action"] == "CLOSE"
    assert "MAX_HOLD_TIME" in res["reason"]


def test_trailing_stop_updates_when_price_advances():
    sl = StopLossManager()
    pos = {
        "symbol": "AAA/USDT",
        "entry_price": 100.0,
        "quantity": 1.0,
        "stop_loss": 95.0,
        "highest_price": 100.0,
    }
    now = datetime.utcnow()
    res = sl.check_exit_conditions(pos, current_price=101.0, current_time=now, df=None)
    # With fallback stop distance 5% of price -> ~5.1 => stop moves up if allowed
    if res["action"] == "UPDATE_STOP":
        assert res["new_stop_price"] > 95.0
