from pathlib import Path
from src.utils.state_manager import StateManager


def test_state_manager_save_and_load(tmp_path: Path):
    state_file = tmp_path / "data" / "state.json"
    stats_file = tmp_path / "data" / "stats.json"
    sm = StateManager(filepath=str(state_file), stats_filepath=str(stats_file))

    sm.save_state({"positions": {"BTC/USDT": {"qty": 1}}})
    data = sm.load_state()
    assert "last_updated" in data
    assert data["positions"]["BTC/USDT"]["qty"] == 1

    sm.save_stats({"trades": 5})
    stats = sm.load_stats()
    assert "last_updated" in stats
    assert stats["trades"] == 5
