from src.database import DatabaseHandler


def test_database_log_and_trade_flow():
    db = DatabaseHandler(db_path="data/test_db_unit.sqlite")

    db.log_message("INFO", "unit test message")
    logs = db.get_logs(limit=10)
    assert isinstance(logs, list)
    assert len(logs) >= 1

    db.add_trade(symbol="AAA/USDT", action="ENTRY", price=100.0, amount=1.0, pnl_pct=0.0,
                 features={"rsi": 55}, score=1.2, status="OPEN")
    trades = db.get_trades(limit=10)
    assert isinstance(trades, list)
    assert len(trades) >= 1
    t = trades[0]
    assert t["symbol"] == "AAA/USDT"
    assert t["action"] in ("ENTRY", "EXIT")
