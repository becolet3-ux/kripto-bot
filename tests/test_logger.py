from src.utils.logger import logger


def test_logger_no_tokens_no_alerts(monkeypatch):
    # Ensure tokens are None to skip HTTP
    monkeypatch.setattr(logger, "tg_token", None, raising=False)
    monkeypatch.setattr(logger, "tg_chat_id", None, raising=False)
    before = getattr(logger, "last_alert_time", 0)
    logger.log("INFO test message")
    logger.log("⚠️ WARNING: test warn")
    logger.log("❌ ERROR: test error")
    after = getattr(logger, "last_alert_time", 0)
    # With tokens None, timestamp should not advance via send_telegram_alert
    assert after == before
