"""CLI: python -m eval.run_eval --event iran_war."""

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List

from agent_ripple import generate_ripple_tree
from config import load_event
from data_market import get_price_changes
from eval.market_integrity import run as run_market_integrity
from eval.qa_faithfulness import run_qa_eval
from eval.retrieval import run_retrieval_eval
from eval.ripple_groundedness import check_price_integrity, score


def _load_queries() -> Dict:
    return json.loads(Path("eval/test_queries.json").read_text())


def _load_ground_truth_sectors() -> List[str]:
    text = Path("eval/wikipedia_ground_truth.md").read_text()
    sectors: List[str] = []
    in_core = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "## Core sectors directly impacted (used for matching)":
            in_core = True
            continue
        if in_core and line.startswith("## "):
            break
        if in_core and line.startswith("- "):
            sectors.append(line[2:].split("(")[0].strip())
    return sectors


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def main(argv=None) -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--out-dir", default="eval/results")
    args = parser.parse_args(argv)

    cfg = load_event(args.event)
    as_of = date.fromisoformat(args.as_of) if args.as_of else cfg.end_date
    queries = _load_queries()

    retrieval_report = run_retrieval_eval(
        queries["retrieval"], cfg=cfg, k=5, use_rewriter=True
    )
    qa_report = run_qa_eval(queries["qa"], cfg, as_of)

    tree = generate_ripple_tree(
        "Major macro event: " + cfg.display_name,
        cfg,
        as_of=as_of,
        max_depth=3,
    )
    truth_sectors = _load_ground_truth_sectors()
    ripple_report = score(tree, truth_sectors)
    price_integrity_report = check_price_integrity(
        tree,
        get_price_changes(cfg, as_of=as_of),
        tolerance=0.5,
    )

    market_report = run_market_integrity(queries["market_integrity"])

    markdown = [
        "# Evaluation Report",
        f"- Event: {cfg.display_name}",
        f"- As of: {as_of.isoformat()}",
        f"- Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## §9.1 Retrieval (precision@5)",
        f"- **Mean precision@5: {retrieval_report['mean_precision']:.2f}**  (target ≥ 0.80)",
        f"- Query rewriting: {'enabled' if retrieval_report.get('use_rewriter') else 'disabled'}",
        "",
        "## §9.2 Ripple tree groundedness",
        f"- AI-generated sectors: {len(ripple_report['ai_sectors'])}",
        f"- Ground-truth sectors: {len(ripple_report['truth_sectors'])}",
        f"- **Precision: {_fmt_pct(ripple_report['precision'])}** · **Recall: {_fmt_pct(ripple_report['recall'])}**",
        f"- Matched: {', '.join(ripple_report['matched']) or '—'}",
        f"- Missed (truth → not in tree): {', '.join(ripple_report['missed']) or '—'}",
        f"- Hallucinated (tree → not in truth): {', '.join(ripple_report['hallucinated']) or '—'}",
        "",
        "### Price integrity (within ±0.5%)",
        f"- Matched: {price_integrity_report['ok_count']}   Mismatched: {price_integrity_report['mismatch_count']}",
        "",
        "## §9.3 QA faithfulness",
        f"- **Mean faithfulness: {qa_report['mean']:.2f}**",
        "",
        "## §9.4 Market data integrity",
        f"- Spot checks: {market_report['ok_count']} / {market_report['ok_count'] + market_report['missing_count']}  passed",
        "",
    ]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report_path = out_dir / f"eval-{args.event}-{stamp}.md"
    report_path.write_text("\n".join(markdown))

    (out_dir / f"eval-{args.event}-{stamp}.json").write_text(json.dumps({
        "retrieval": retrieval_report,
        "ripple": ripple_report,
        "price_integrity": price_integrity_report,
        "qa": qa_report,
        "market_integrity": market_report,
    }, indent=2, default=str))

    print(f"Wrote {report_path}")
    return str(report_path)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
