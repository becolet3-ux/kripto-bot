from datetime import datetime, timedelta
from src.execution.stop_loss_manager import StopLossManager


def test_dynamic_roi_close_trigger():
    sl = StopLossManager()
    past = datetime.utcnow() - timedelta(minutes=60)  # ROI target should be ~3%
    pos = {
        "symbol": "AAA/USDT",
        "entry_price": 100.0,
        "quantity": 1.0,
        "entry_timestamp": past.isoformat(),
    }
    now = datetime.utcnow()
    res = sl.check_exit_conditions(pos, current_price=103.5, current_time=now, df=None)
    assert res["action"] == "CLOSE"
    assert "DYNAMIC_ROI_HIT" in res["reason"]


def test_time_based_no_profit_exit():
    sl = StopLossManager()
    past = datetime.utcnow() - timedelta(hours=24, minutes=1)
    pos = {
        "symbol": "AAA/USDT",
        "entry_price": 100.0,
        "quantity": 1.0,
        "entry_timestamp": past.isoformat(),
    }
    now = datetime.utcnow()
    res = sl.check_exit_conditions(pos, current_price=99.0, current_time=now, df=None)
    assert res["action"] == "CLOSE"
    assert "TIME_BASED_NO_PROFIT" in res["reason"]
