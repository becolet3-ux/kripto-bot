from pathlib import Path
from src.learning.brain import BotBrain


def test_brain_update_weights_and_record_outcome(tmp_path: Path):
    brain = BotBrain(data_file=str(tmp_path / "learning.json"))
    msg = brain.record_outcome(
        symbol="AAA/USDT",
        pnl_pct=3.0,
        entry_features={"strategy": "trend_following", "indicator_signals": {"rsi": 1}},
        entry_price=100.0,
        exit_price=103.0,
    )
    s = brain.memory["global_stats"]
    assert s["total_trades"] == 1
    assert s["wins"] == 1
    assert s["win_rate"] > 0
    w = brain.get_weights()
    assert w["trend_following"] >= 1.0


def test_brain_ghost_trades_flow(tmp_path: Path):
    brain = BotBrain(data_file=str(tmp_path / "learning.json"))
    brain.record_ghost_trade("BBB/USDT", entry_price=100.0, reason="test", signal_score=10.0)
    # Price jumps -> TP
    brain.update_ghost_trades({"BBB/USDT": 106.0})
    ghosts = brain.memory.get("ghost_trades", [])
    assert ghosts
    closed = [g for g in ghosts if g.get("status") == "CLOSED"]
    assert closed and closed[0]["exit_reason"] in ("TP_HIT", "SL_HIT", "EXPIRED")


def test_brain_check_safety_defaults(tmp_path: Path):
    brain = BotBrain(data_file=str(tmp_path / "learning.json"))
    res = brain.check_safety("AAA/USDT", current_volatility=1.0, volume_ratio=1.0, current_rsi=50.0)
    assert res["safe"] is True
