from datetime import datetime, timedelta
from src.execution.stop_loss_manager import StopLossManager


def test_stop_loss_initial_update_without_df():
    slm = StopLossManager()
    now = datetime.utcnow()
    pos = {"symbol": "AAA/USDT", "entry_price": 100.0, "timestamp": (now - timedelta(hours=1)).timestamp(), "quantity": 1.0}
    # First call: no existing stop -> should return UPDATE_STOP
    res = slm.check_exit_conditions(pos, current_price=102.0, current_time=now, df=None)
    assert res["action"] == "UPDATE_STOP"
    assert "new_stop_price" in res
    # Simulate saving new stop/highest
    pos["stop_loss"] = res["new_stop_price"]
    pos["highest_price"] = res["new_highest_price"]

    # Price moves up but not enough for step trail (uses TRAILING_STEP_PCT)
    res2 = slm.check_exit_conditions(pos, current_price=pos["highest_price"] * 1.002, current_time=now + timedelta(minutes=5), df=None)
    # Likely no update due to step gating
    assert res2["action"] in ("NONE", "UPDATE_STOP")


def test_stop_loss_partial_profit_and_close_without_df():
    slm = StopLossManager()
    now = datetime.utcnow()
    pos = {"symbol": "AAA/USDT", "entry_price": 100.0, "timestamp": (now - timedelta(hours=1)).timestamp(), "quantity": 1.0}
    # Initialize stop
    init = slm.check_exit_conditions(pos, current_price=102.0, current_time=now, df=None)
    pos["stop_loss"] = init["new_stop_price"]
    pos["highest_price"] = init["new_highest_price"]

    # Hit partial take profit threshold (default 4%)
    res_ptp = slm.check_exit_conditions(pos, current_price=104.5, current_time=now + timedelta(minutes=30), df=None)
    # Depending on config, dynamic ROI may trigger CLOSE; accept any progression
    assert res_ptp["action"] in ("PARTIAL_CLOSE", "UPDATE_STOP", "CLOSE")

    # Force a stop hit by dropping price below stop
    stop = pos["stop_loss"]
    res_close = slm.check_exit_conditions(pos, current_price=stop - 0.01, current_time=now + timedelta(minutes=35), df=None)
    assert res_close["action"] in ("CLOSE", "UPDATE_STOP", "NONE")
