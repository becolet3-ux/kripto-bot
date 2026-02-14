import os
import importlib


def test_dashboard_import_and_helpers(tmp_path, monkeypatch):
    # Point state and log files to temp to avoid reading real files
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "state.json"))
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "bot.log"))

    # Create dummy files
    (tmp_path / "state.json").write_text("{}")
    (tmp_path / "bot.log").write_text("line1\nline2\n")

    mod = importlib.import_module("src.dashboard")
    assert hasattr(mod, "load_json")
    assert hasattr(mod, "load_logs")

    # Verify helpers work
    assert mod.load_json(os.environ["STATE_FILE"]) == {}
    logs = mod.load_logs(os.environ["LOG_FILE"], lines=1)
    assert isinstance(logs, list) and len(logs) >= 1
