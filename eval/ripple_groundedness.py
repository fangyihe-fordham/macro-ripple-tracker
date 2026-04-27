from typing import Dict, List


def _flatten_sectors(tree: Dict) -> List[str]:
    out: List[str] = []

    def _walk(nodes: List[Dict]) -> None:
        for node in nodes:
            out.append(node.get("sector", ""))
            _walk(node.get("children", []))

    _walk(tree.get("nodes", []))
    return [sector for sector in out if sector]


def _fuzzy_contains(ai_sector: str, truth_sector: str) -> bool:
    ai = ai_sector.lower()
    truth = truth_sector.lower()
    parts = [part.strip() for part in truth.split("/")] + [truth]
    return any(part in ai for part in parts if part)


def score(tree: Dict, truth_sectors: List[str]) -> Dict:
    ai_sectors = _flatten_sectors(tree)
    matched_truths = set()
    matched_ai = set()

    for truth in truth_sectors:
        for ai in ai_sectors:
            if _fuzzy_contains(ai, truth) or _fuzzy_contains(truth, ai):
                matched_truths.add(truth)
                matched_ai.add(ai)
                break

    missed = [truth for truth in truth_sectors if truth not in matched_truths]
    hallucinated = [ai for ai in ai_sectors if ai not in matched_ai]
    precision = len(matched_ai) / len(ai_sectors) if ai_sectors else 0.0
    recall = len(matched_truths) / len(truth_sectors) if truth_sectors else 0.0

    return {
        "ai_sectors": ai_sectors,
        "truth_sectors": truth_sectors,
        "matched": sorted(matched_truths),
        "missed": sorted(missed),
        "hallucinated": sorted(hallucinated),
        "precision": precision,
        "recall": recall,
    }


def check_price_integrity(tree: Dict, actual_changes: Dict, tolerance: float = 0.5) -> Dict:
    oks: List[Dict] = []
    mismatches: List[Dict] = []

    def _walk(nodes: List[Dict]) -> None:
        for node in nodes:
            for detail in node.get("price_details", []) or []:
                symbol = detail.get("symbol")
                claimed = detail.get("pct_change")
                actual = (actual_changes.get(symbol) or {}).get("pct_change")
                if actual is None or claimed is None:
                    continue
                if abs(claimed - actual) <= tolerance:
                    oks.append({"symbol": symbol, "claimed": claimed, "actual": actual})
                else:
                    mismatches.append({
                        "symbol": symbol,
                        "claimed": claimed,
                        "actual": actual,
                        "delta": claimed - actual,
                    })
            _walk(node.get("children", []))

    _walk(tree.get("nodes", []))
    return {
        "ok_count": len(oks),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "ok": oks,
    }
