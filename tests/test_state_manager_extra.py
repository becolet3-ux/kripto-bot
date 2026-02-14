import json
import os
from src.utils.state_manager import StateManager


def test_load_state_and_stats_when_missing(tmp_path):
    state_path = tmp_path / "data" / "bot_state.json"
    stats_path = tmp_path / "data" / "bot_stats.json"
    sm = StateManager(filepath=str(state_path), stats_filepath=str(stats_path))

    # ensure_dir should create files
    assert os.path.exists(state_path)
    assert os.path.exists(stats_path)

    # Load defaults
    state = sm.load_state()
    stats = sm.load_stats()
    assert isinstance(state, dict)
    assert isinstance(stats, dict)


def test_corrupted_files_return_empty(tmp_path):
    state_path = tmp_path / "data" / "bot_state.json"
    stats_path = tmp_path / "data" / "bot_stats.json"
    sm = StateManager(filepath=str(state_path), stats_filepath=str(stats_path))

    # Write corrupted content
    state_path.write_text("{not-json")
    stats_path.write_text("{not-json")

    # Should not raise and should return {}
    assert sm.load_state() == {}
    assert sm.load_stats() == {}


def test_save_state_and_stats_add_timestamp(tmp_path):
    state_path = tmp_path / "data" / "bot_state.json"
    stats_path = tmp_path / "data" / "bot_stats.json"
    sm = StateManager(filepath=str(state_path), stats_filepath=str(stats_path))

    sm.save_state({"a": 1})
    sm.save_stats({"b": 2})

    # Read raw files to verify JSON contains keys
    data_state = json.loads(state_path.read_text())
    data_stats = json.loads(stats_path.read_text())

    assert "last_updated" in data_state and data_state["a"] == 1
    assert "last_updated" in data_stats and data_stats["b"] == 2
