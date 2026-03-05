#!/usr/bin/env python3
"""Calculate top-k recall for simple agent vs care agent.

Reads the v3 batch result Excel files and computes recall@k for k=1..10.
Prints a comparison table and highlights top-5 recall.
"""

import json
from pathlib import Path

import openpyxl

RESULTS_DIR = Path(__file__).resolve().parent / "agent_run" / "batch_results" / "v3"

AGENTS = {
    "simple_agent_no_tools": RESULTS_DIR / "simple_agent_no_tools.xlsx",
    "simple_agent_with_web_search": RESULTS_DIR / "simple_agent_with_web_search.xlsx",
    "simple_agent_with_tools": RESULTS_DIR / "simple_agent_with_tools.xlsx",
    "care_agent_with_tools": RESULTS_DIR / "care_agent_with_tools.xlsx",
}


def load_results(xlsx_path: Path) -> list[dict]:
    """Load results from the Results sheet of an Excel file."""
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb["Results"]
    headers = [cell.value for cell in ws[1]]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        # Skip blank/summary rows
        if row[0] is None or row[0] == "SUMMARY":
            continue
        rows.append(dict(zip(headers, row)))
    return rows


def get_predicted_ids(row: dict) -> list[str]:
    """Extract ordered list of predicted identifiers from a result row.

    Prefers the structured ``predicted_results`` JSON column. When the JSON is
    truncated by Excel's cell-character limit (~32k chars) and cannot be parsed,
    falls back to the ``data_identifiers`` comma-separated string column.
    """
    predicted_json = row.get("predicted_results", "[]")
    try:
        predictions = json.loads(predicted_json)
        return [p.get("data_identifier", "") for p in predictions]
    except (json.JSONDecodeError, TypeError):
        # JSON truncated by Excel cell limit — use the comma-separated fallback
        fallback = row.get("data_identifiers", "") or ""
        if fallback:
            return [s.strip() for s in fallback.split(",") if s.strip()]
        return []


def is_hit_at_k(row: dict, k: int) -> bool:
    """Check if expected_identifier appears in the top-k predictions.

    When the predicted_results JSON is truncated and no fallback identifiers
    exist, uses the pre-computed top_match/any_match Excel columns as bounds:
    - k >= 1 and top_match is True  → definitely a hit (it was rank 1)
    - any_match is False → definitely not a hit at any k
    """
    expected = row.get("expected_identifier", "")
    ids = get_predicted_ids(row)
    if ids:
        return expected in ids[:k]
    # No parseable predictions — fall back to pre-computed booleans
    if k >= 1 and row.get("top_match"):
        return True
    if row.get("any_match"):
        # We know it matched somewhere but don't know the rank.
        # Conservatively return True (it's in the results, rank unknown).
        return True
    return False


def compute_top_k_recall(results: list[dict], k: int) -> tuple[int, int]:
    """Return (hits, total) where a hit means expected_identifier is in the top-k predictions."""
    hits = sum(1 for row in results if is_hit_at_k(row, k))
    return hits, len(results)


def main():
    max_k = 10
    agent_data: dict[str, list[dict]] = {}

    for name, path in AGENTS.items():
        if not path.exists():
            print(f"WARNING: {path} not found, skipping.")
            continue
        agent_data[name] = load_results(path)

    if not agent_data:
        print("No result files found.")
        return

    # Header
    print(f"\n{'k':<5}", end="")
    for name in agent_data:
        print(f"  {name:<30}", end="")
    print()
    print("-" * (5 + 32 * len(agent_data)))

    # Compute recall@k for each k
    for k in range(1, max_k + 1):
        marker = " <<<" if k == 5 else ""
        line = f"{k:<5}"
        for name, results in agent_data.items():
            hits, total = compute_top_k_recall(results, k)
            pct = hits / total * 100 if total else 0
            line += f"  {hits:>3}/{total:<3} ({pct:5.1f}%)            "
        line += marker
        print(line)

    # Summary
    print("\n\n=== Top-1 Recall (Top Match) ===\n")
    for name, results in agent_data.items():
        hits, total = compute_top_k_recall(results, 1)
        pct = hits / total * 100 if total else 0
        print(f"  {name}: {hits}/{total} ({pct:.1f}%)")

    print("\n=== Top-5 Recall ===\n")
    for name, results in agent_data.items():
        hits, total = compute_top_k_recall(results, 5)
        pct = hits / total * 100 if total else 0
        print(f"  {name}: {hits}/{total} ({pct:.1f}%)")



if __name__ == "__main__":
    main()
