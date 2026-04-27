from eval import market_integrity


def test_spot_check_matches(monkeypatch):
    monkeypatch.setattr(market_integrity, "get_price_on_date",
                        lambda sym, d: {"BZ=F": 88.5, "XLE": None}.get(sym))

    pairs = [
        {"symbol": "BZ=F", "date": "2026-03-02"},
        {"symbol": "XLE", "date": "2026-03-02"},
    ]

    report = market_integrity.run(pairs)

    assert report["ok_count"] == 1
    assert report["missing_count"] == 1
    assert report["results"][0]["close"] == 88.5
    assert report["results"][1]["close"] is None
