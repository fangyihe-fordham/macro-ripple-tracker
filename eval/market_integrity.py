from datetime import date
from typing import Dict, List

from data_market import get_price_on_date


def run(pairs: List[Dict]) -> Dict:
    results = []
    ok_count = 0
    missing_count = 0

    for pair in pairs:
        target_date = date.fromisoformat(pair["date"])
        close = get_price_on_date(pair["symbol"], target_date)
        results.append({
            "symbol": pair["symbol"],
            "date": pair["date"],
            "close": close,
        })
        if close is None:
            missing_count += 1
        else:
            ok_count += 1

    return {
        "metric": "market_integrity",
        "ok_count": ok_count,
        "missing_count": missing_count,
        "results": results,
    }
