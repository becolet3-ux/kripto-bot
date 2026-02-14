import src.strategies.multi_timeframe as mtf


def test_mtf_perfect_alignment(monkeypatch):
    def fake_analyze(symbol, timeframe, exchange):
        return {"direction": "LONG", "trend_strength": "STRONG", "indicators": {}, "confidence": 1.0}
    monkeypatch.setattr(mtf, "analyze_single_timeframe", fake_analyze)
    res = mtf.multi_timeframe_analyzer("AAA/USDT", exchange=object())
    assert res["consensus"] is True
    assert res["direction"] == "LONG"
    assert res["confidence_multiplier"] == 1.30


def test_mtf_block_by_4h_opposite(monkeypatch):
    def fake_analyze(symbol, timeframe, exchange):
        if timeframe in ("15m", "1h"):
            return {"direction": "LONG", "trend_strength": "STRONG", "indicators": {}, "confidence": 1.0}
        return {"direction": "SHORT", "trend_strength": "STRONG", "indicators": {}, "confidence": 1.0}
    monkeypatch.setattr(mtf, "analyze_single_timeframe", fake_analyze)
    res = mtf.multi_timeframe_analyzer("AAA/USDT", exchange=object())
    assert res["consensus"] is False
    assert "counter-trend" in res["blocking_reason"]


def test_mtf_4h_1h_align(monkeypatch):
    def fake_analyze(symbol, timeframe, exchange):
        if timeframe in ("4h", "1h"):
            return {"direction": "LONG", "trend_strength": "STRONG", "indicators": {}, "confidence": 1.0}
        return {"direction": "NEUTRAL", "trend_strength": "WEAK", "indicators": {}, "confidence": 0.0}
    monkeypatch.setattr(mtf, "analyze_single_timeframe", fake_analyze)
    res = mtf.multi_timeframe_analyzer("AAA/USDT", exchange=object())
    assert res["consensus"] is True
    assert res["direction"] == "LONG"
    assert res["confidence_multiplier"] == 1.15
