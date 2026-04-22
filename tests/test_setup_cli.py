import json

import pandas as pd


def test_setup_runs_end_to_end(tmp_data_dir, monkeypatch, fixtures_dir):
    import data_news.gdelt as gdelt_mod
    import data_news.newsapi_fetcher as newsapi_mod
    import data_news.rss as rss_mod
    import data_market

    monkeypatch.setattr(gdelt_mod, "fetch", lambda cfg: [
        {"url": "https://g.com/1", "headline": "Iran Hormuz closed", "source": "g.com",
         "date": "2026-03-01", "snippet": "Oil surged.", "full_text": "",
         "source_kind": "gdelt"},
    ])
    monkeypatch.setattr(newsapi_mod, "fetch", lambda cfg, max_pages=1: [])
    monkeypatch.setattr(rss_mod, "fetch", lambda cfg: [
        {"url": "https://r.com/1", "headline": "Shipping delays on Hormuz", "source": "r.com",
         "date": "2026-03-02", "snippet": "Vessels reroute.", "full_text": "",
         "source_kind": "rss"},
    ])

    fake_df = pd.read_csv(fixtures_dir / "yf_brent_sample.csv", parse_dates=["Date"]).set_index("Date")
    monkeypatch.setattr(data_market.yf, "download",
                        lambda *a, **kw: fake_df.copy())

    import setup as setup_mod
    setup_mod.main(["--event", "iran_war"])

    arts_path = tmp_data_dir / "articles.json"
    manifest_path = tmp_data_dir / "manifest.json"
    prices_dir = tmp_data_dir / "prices"

    arts = json.loads(arts_path.read_text())
    assert len(arts) == 2
    manifest = json.loads(manifest_path.read_text())
    assert manifest["event"] == "iran_war"
    assert manifest["article_count"] == 2
    assert "snapshot_utc" in manifest
    assert prices_dir.exists() and len(list(prices_dir.glob("*.csv"))) == 11

    from data_news import retrieve
    hits = retrieve("oil price Hormuz", top_k=1)
    assert len(hits) == 1
