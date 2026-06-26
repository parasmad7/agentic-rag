"""Terminal and JSON reporting for eval results."""

from __future__ import annotations

import json
import time
from pathlib import Path

from evals.judges import Scores


def _bar(value: float, width: int = 15) -> str:
    filled = int(value * width)
    return "█" * filled + "░" * (width - filled)


def _color(value: float) -> str:
    if value >= 0.8:
        return f"\033[92m{value:.2f}\033[0m"
    if value >= 0.5:
        return f"\033[93m{value:.2f}\033[0m"
    return f"\033[91m{value:.2f}\033[0m"


def print_case_result(
    case_id: str,
    question: str,
    scores: Scores,
    latency: float,
    error: str | None = None,
):
    print(f"\n  {'─' * 70}")
    print(f"  {case_id}")
    print(f"  Q: {question[:80]}")
    if error:
        print(f"  \033[91mERROR: {error}\033[0m")
        return
    print(f"  Tool routing:    {_bar(scores.tool_routing)} {_color(scores.tool_routing)}")
    print(f"  Source coverage: {_bar(scores.source_coverage)} {_color(scores.source_coverage)}")
    print(f"  Faithfulness:    {_bar(scores.faithfulness)} {_color(scores.faithfulness)}")
    print(f"  Relevance:       {_bar(scores.relevance)} {_color(scores.relevance)}")
    print(f"  Correctness:     {_bar(scores.correctness)} {_color(scores.correctness)}")
    print(f"  Efficiency:      {_bar(scores.efficiency)} {_color(scores.efficiency)}")
    print(f"  Latency:         {latency:.1f}s")


def print_summary(results: list[dict]):
    print(f"\n{'=' * 74}")
    print("  EVAL SUMMARY")
    print(f"{'=' * 74}")

    scored = [r for r in results if r.get("scores") and not r.get("error")]
    errored = [r for r in results if r.get("error")]

    if not scored:
        print("  No successful evaluations.")
        return

    dims = ["tool_routing", "source_coverage", "faithfulness", "relevance", "correctness", "efficiency"]
    avgs = {}
    for d in dims:
        vals = [getattr(r["scores"], d) for r in scored]
        avgs[d] = sum(vals) / len(vals)

    composite = sum(avgs.values()) / len(dims)

    print(f"\n  Cases: {len(scored)} passed, {len(errored)} failed, {len(results)} total")
    print(f"  Total time: {sum(r['latency'] for r in results):.1f}s")
    print()

    for d in dims:
        label = d.replace("_", " ").title()
        print(f"  {label:18s} {_bar(avgs[d])} {_color(avgs[d])}")

    print(f"\n  {'─' * 40}")
    print(f"  {'Composite':18s} {_bar(composite)} {_color(composite)}")
    print()

    # Breakdown by category
    categories: dict[str, list[dict]] = {}
    for r in scored:
        cat = r.get("category", "unknown")
        categories.setdefault(cat, []).append(r)

    if len(categories) > 1:
        print(f"  By category:")
        for cat, cat_results in sorted(categories.items()):
            cat_composite_vals = []
            for r in cat_results:
                s = r["scores"]
                cat_composite_vals.append(
                    sum(getattr(s, d) for d in dims) / len(dims)
                )
            cat_avg = sum(cat_composite_vals) / len(cat_composite_vals)
            print(f"    {cat:20s} {_bar(cat_avg)} {_color(cat_avg)}  (n={len(cat_results)})")
        print()

    if errored:
        print(f"  Errors:")
        for r in errored:
            print(f"    {r['case_id']}: {r['error'][:80]}")
        print()


def save_json_report(results: list[dict], output_dir: str = "evals/results"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_file = out_path / f"eval_{timestamp}.json"

    scored = [r for r in results if r.get("scores") and not r.get("error")]
    dims = ["tool_routing", "source_coverage", "faithfulness", "relevance", "correctness", "efficiency"]

    avgs = {}
    for d in dims:
        vals = [getattr(r["scores"], d) for r in scored]
        avgs[d] = round(sum(vals) / len(vals), 3) if vals else 0.0

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_cases": len(results),
        "passed": len(scored),
        "failed": len(results) - len(scored),
        "total_latency_s": round(sum(r["latency"] for r in results), 2),
        "averages": avgs,
        "composite": round(sum(avgs.values()) / len(dims), 3) if avgs else 0.0,
        "cases": [
            {
                "case_id": r["case_id"],
                "question": r["question"],
                "category": r.get("category"),
                "difficulty": r.get("difficulty"),
                "scores": r["scores"].model_dump() if r.get("scores") else None,
                "latency_s": round(r["latency"], 2),
                "error": r.get("error"),
                "answer_preview": r.get("answer", "")[:300],
            }
            for r in results
        ],
    }

    report_file.write_text(json.dumps(report, indent=2))
    print(f"  Report saved: {report_file}")
    return str(report_file)
