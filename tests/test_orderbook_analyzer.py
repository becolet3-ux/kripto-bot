from src.market_structure.orderbook_analyzer import OrderBookAnalyzer


def make_orderbook(bid_base=100.0, ask_base=100.2, bid_qty=10.0, ask_qty=5.0, big_wall=None):
    bids = [[bid_base - i*0.01, bid_qty] for i in range(30)]
    asks = [[ask_base + i*0.01, ask_qty] for i in range(30)]
    if big_wall and big_wall["side"] == "bid":
        # Large support close to price
        bids.insert(0, [big_wall.get("price", bid_base * 0.995), big_wall.get("qty", bid_qty * 100)])
    if big_wall and big_wall["side"] == "ask":
        asks.insert(0, [big_wall.get("price", ask_base * 1.005), big_wall.get("qty", ask_qty * 100)])
    return {"bids": bids, "asks": asks}


def test_orderbook_buy_pressure_and_support_wall():
    oba = OrderBookAnalyzer()
    ob = make_orderbook(bid_qty=20.0, ask_qty=5.0, big_wall={"side": "bid", "qty": 500.0})
    analysis = oba.analyze_depth(ob, current_price=100.0)
    assert analysis["pressure"] in ("BUY_PRESSURE", "NEUTRAL")
    score = oba.get_score_impact(analysis)
    assert score >= 0.5


def test_orderbook_sell_pressure_and_resistance_wall():
    oba = OrderBookAnalyzer()
    ob = make_orderbook(bid_qty=5.0, ask_qty=20.0, big_wall={"side": "ask", "qty": 500.0})
    analysis = oba.analyze_depth(ob, current_price=100.0)
    assert analysis["pressure"] in ("SELL_PRESSURE", "NEUTRAL")
    score = oba.get_score_impact(analysis)
    assert score <= -0.5
