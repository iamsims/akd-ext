"""Batch runner for PDS agent configurations.

Reads queries from an input spreadsheet, runs each through a specified
agent configuration, and writes results to an Excel file.

Usage:
    uv run python care-process/agent_run/batch_run.py \
        --input care-process/batch_results/run_20260214_002038/results/results_spreadsheet.xlsx \
        --config simple_agent_no_tools

    uv run python care-process/agent_run/batch_run.py \
        --input care-process/batch_results/run_20260214_002038/results/results_spreadsheet.xlsx \
        --config simple_agent_with_tools

    uv run python care-process/agent_run/batch_run.py \
        --input care-process/batch_results/run_20260214_002038/results/results_spreadsheet.xlsx \
        --config care_agent_with_tools

    # Run only 5 pending queries (useful for debugging / quick tests)
    uv run python care-process/agent_run/batch_run.py \
        --input care-process/batch_results/run_20260214_002038/results/results_spreadsheet.xlsx \
        --config simple_agent_no_tools --limit 5
"""

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# Ensure care-process is on sys.path so `utils` and `agent_run` imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_run.simple_agent_with_tools import run, AgentConfig, CareDatasetResults
from agent_run.prompts.simple_agent import simple_agent_prompt
from agent_run.prompts.simple_agent_with_tools import simple_agent_with_tools_prompt
from agent_run.prompts.care_agent import care_prompt



CONFIGS: dict[str, AgentConfig] = {
    "simple_agent_no_tools": AgentConfig(
        system_prompt=simple_agent_prompt,
        use_mcp_tools=False,
        model="gpt-5.2",
        reasoning_effort="high",
    ),
    "simple_agent_with_web_search": AgentConfig(
        system_prompt=simple_agent_with_tools_prompt,
        use_mcp_tools=False,
        use_web_search=True,
        model="gpt-5.2",
        reasoning_effort="high",
    ),
    "simple_agent_with_tools": AgentConfig(
        system_prompt=simple_agent_with_tools_prompt,
        use_mcp_tools=True,
        model="gpt-5.2",
        reasoning_effort="high",
    ),
    "care_agent_with_tools": AgentConfig(
        system_prompt=care_prompt,
        use_mcp_tools=True,
        output_type=CareDatasetResults,
        model="gpt-5.2",
        reasoning_effort="high",
    ),
    "simple_agent_with_tools_web_search": AgentConfig(
        system_prompt=simple_agent_with_tools_prompt,
        use_mcp_tools=True,
        use_web_search=True,
        model="gpt-5.2",
        reasoning_effort="high",
    ),
    # ---- Category-scoped CARE agent variants ----
    # Single-category ablations
    "care_agent_catalog_only": AgentConfig(
        system_prompt=care_prompt,
        use_mcp_tools=True,
        output_type=CareDatasetResults,
        model="gpt-5.2",
        reasoning_effort="high",
        tool_categories=["pds_catalog"],
    ),
    "care_agent_pds4_only": AgentConfig(
        system_prompt=care_prompt,
        use_mcp_tools=True,
        output_type=CareDatasetResults,
        model="gpt-5.2",
        reasoning_effort="high",
        tool_categories=["pds4"],
    ),
    "care_agent_node_only": AgentConfig(
        system_prompt=care_prompt + "\n Note: PDS4_MCP and PDS_CATALOG_MCP are unavailable in this run; work with node-specific tools instead",
        use_mcp_tools=True,
        output_type=CareDatasetResults,
        model="gpt-5.2",
        reasoning_effort="high",
        tool_categories=["node_specific"],
    ),
    # Pairwise combinations
    "care_agent_catalog_and_pds4": AgentConfig(
        system_prompt=care_prompt + "\n Note: Node-specific tools are unavailable in this run; work with PDS_CATALOG_MCP and PDS4_MCP instead",
        use_mcp_tools=True,
        output_type=CareDatasetResults,
        model="gpt-5.2",
        reasoning_effort="high",
        tool_categories=["pds_catalog", "pds4"],
    ),
    "care_agent_catalog_and_node": AgentConfig(
        system_prompt=care_prompt + "\n Note: PDS4_MCP is unavailable in this run; work with PDS4_CATALOG_MCP instead",
        use_mcp_tools=True,
        output_type=CareDatasetResults,
        model="gpt-5.2",
        reasoning_effort="high",
        tool_categories=["pds_catalog", "node_specific"],
    ),
    "care_agent_pds4_and_node": AgentConfig(
        system_prompt=care_prompt + "\n Note: PDS_CATALOG_MCP is unavailable in this run; work with PDS4_MCP instead",
        use_mcp_tools=True,
        output_type=CareDatasetResults,
        model="gpt-5.2",
        reasoning_effort="high",
        tool_categories=["pds4", "node_specific"],
    ),
}


# one with only api, 
# one with api + tools + catalog (scraped data) tool 
# one with api + tools

RESULTS_DIR = Path(__file__).resolve().parent / "batch_results" / "tool_comparision_benchmark"


def _git_info() -> dict:
    """Capture current git commit, branch, and dirty status."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    info = {}
    try:
        info["commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
        ).strip()
        info["commit_short"] = info["commit"][:8]
        info["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, text=True
        ).strip()
        info["dirty"] = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo_root, text=True
        ).strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        info["commit"] = "unknown"
        info["branch"] = "unknown"
        info["dirty"] = None
    return info


def save_run_config(
    config_name: str,
    config: AgentConfig,
    input_path: str,
    output_path: Path,
    concurrency: int,
    limit: int | None,
):
    """Save a JSON config file capturing the full run parameters for reproducibility."""
    git = _git_info()
    run_config = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git": git,
        "config_name": config_name,
        "agent_config": {
            "model": config.model,
            "reasoning_effort": config.reasoning_effort,
            "use_mcp_tools": config.use_mcp_tools,
            "use_web_search": config.use_web_search,
            "tool_categories": config.tool_categories,
            "timeout": config.timeout,
            "system_prompt": config.system_prompt,
        },
        "input_path": str(input_path),
        "output_path": str(output_path),
        "concurrency": concurrency,
        "limit": limit,
    }
    config_path = output_path.with_suffix(".run_config.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(run_config, indent=2))
    print(f"Run config saved to: {config_path}")



def load_queries(input_path: str) -> list[dict]:
    """Load queries from the input spreadsheet."""
    wb = openpyxl.load_workbook(input_path)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        rows.append({
            "paper_name": row[0],
            "query": row[1],
            "expected_identifier": row[2],
            "expected_identifier_type": row[3],
        })
    return rows


def _is_data_row(row: tuple) -> bool:
    """Return True if the row is a real data row (not blank or summary)."""
    return row[0] is not None and row[1] is not None and row[0] != "SUMMARY"


def load_existing_results(output_path: Path) -> set[str]:
    """Load already-processed queries from an existing output file for resume."""
    if not output_path.exists():
        return set()
    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    processed = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if _is_data_row(row):
            processed.add(row[1])
    return processed


def save_results(results: list[dict], all_tool_calls: list[dict], output_path: Path):
    """Write results to an Excel file with formatting.

    ``all_tool_calls`` is a flat list of dicts, each with keys:
    query, tool_call_index, tool_id, tool_name, arguments, output.
    They are written to a second sheet called "Tool Calls".
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Results"

    headers = [
        "paper_name", "query", "expected_identifier", "expected_identifier_type",
        "predicted_results", "top_match", "any_match", "tool_call_count", "total_tokens",
        "number_of_identifiers_returned", "data_identifiers",
    ]

    # Header styling
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Sort results and tool calls by query for consistent ordering
    sorted_results = sorted(results, key=lambda r: r.get("query", ""))
    sorted_tool_calls = sorted(all_tool_calls, key=lambda tc: (tc.get("query", ""), tc.get("tool_call_index", 0)))

    # Data rows
    match_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    no_match_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    for row_idx, result in enumerate(sorted_results, 2):
        for col_idx, key in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=result.get(key))
            if key == "top_match":
                cell.fill = match_fill if result.get(key) else no_match_fill
            elif key == "any_match":
                cell.fill = match_fill if result.get(key) else no_match_fill

    # Summary row
    summary_row = len(sorted_results) + 3
    top_matches = sum(1 for r in sorted_results if r.get("top_match"))
    any_matches = sum(1 for r in sorted_results if r.get("any_match"))
    total_queries = len(sorted_results)
    total_tokens = sum(int(r.get("total_tokens", 0) or 0) for r in sorted_results)

    ws.cell(row=summary_row, column=1, value="SUMMARY").font = Font(bold=True)
    if total_queries:
        ws.cell(row=summary_row, column=2, value=f"Top match: {top_matches}/{total_queries} ({top_matches/total_queries*100:.1f}%) | Any match: {any_matches}/{total_queries} ({any_matches/total_queries*100:.1f}%)")
    else:
        ws.cell(row=summary_row, column=2, value="N/A")
    ws.cell(row=summary_row, column=11, value=f"Total tokens: {total_tokens:,}")

    # Column widths
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 60
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["E"].width = 15
    ws.column_dimensions["F"].width = 60
    ws.column_dimensions["G"].width = 80
    ws.column_dimensions["H"].width = 15
    ws.column_dimensions["I"].width = 15

    # --- Tool Calls sheet ---
    tc_ws = wb.create_sheet("Tool Calls")
    tc_headers = ["query", "tool_call_index", "tool_id", "tool_name", "arguments", "output"]
    for col, header in enumerate(tc_headers, 1):
        cell = tc_ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row_idx, tc in enumerate(sorted_tool_calls, 2):
        for col_idx, key in enumerate(tc_headers, 1):
            tc_ws.cell(row=row_idx, column=col_idx, value=tc.get(key))

    tc_ws.column_dimensions["A"].width = 60
    tc_ws.column_dimensions["D"].width = 30
    tc_ws.column_dimensions["E"].width = 60
    tc_ws.column_dimensions["F"].width = 80

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)


async def batch_run(
    input_path: str,
    config_name: str,
    concurrency: int = 1,
    limit: int | None = None,
    run_id: int | None = None,
    fresh: bool = False,
):
    config = CONFIGS[config_name]
    queries = load_queries(input_path)
    suffix = f"_run{run_id}" if run_id is not None else ""
    output_path = RESULTS_DIR / f"{config_name}{suffix}.xlsx"

    # Save run config for reproducibility
    save_run_config(config_name, config, input_path, output_path, concurrency, limit)

    # Resume support (disabled when fresh=True for independent multi-run)
    already_done: set[str] = set()
    if not fresh:
        already_done = load_existing_results(output_path)
        if already_done:
            print(f"Resuming: {len(already_done)} queries already processed, skipping them.")

    # Load existing results to preserve them (skip when fresh)
    results: list[dict] = []
    all_tool_calls: list[dict] = []
    if not fresh and output_path.exists():
        wb = openpyxl.load_workbook(output_path)
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if _is_data_row(row) and row[1] in already_done:
                results.append(dict(zip(headers, row)))
        # Restore tool calls from the "Tool Calls" sheet if it exists
        if "Tool Calls" in wb.sheetnames:
            tc_ws = wb["Tool Calls"]
            tc_headers = [cell.value for cell in tc_ws[1]]
            for row in tc_ws.iter_rows(min_row=2, values_only=True):
                if row[0] and row[0] in already_done:
                    all_tool_calls.append(dict(zip(tc_headers, row)))

    total = len(queries)
    pending = [q for q in queries if q["query"] not in already_done]

    if limit is not None:
        pending = pending[:limit]
        print(f"LIMIT MODE: capping pending queries to {limit}")

    print(f"Config: {config_name}")
    print(f"Total queries: {total}, pending: {len(pending)}, concurrency: {concurrency}")
    print(f"Output: {output_path}\n")

    semaphore = asyncio.Semaphore(concurrency)
    save_lock = asyncio.Lock()
    completed = {"count": 0}

    async def run_single(i: int, q: dict):
        query_text = q["query"]
        short = query_text[:80] + "..." if len(query_text) > 80 else query_text
        tc_rows: list[dict] = []

        async with semaphore:
            print(f"[{i}/{len(pending)}] {short}")
            try:
                result = await run(query_text, config)
                output = result["output"]
                dataset_results = output.get("results", [])

                # Truncate to 25 results max, then check matches
                expected_id = q["expected_identifier"]
                dataset_results = dataset_results[:25]
                truncated_ids = [r.get("data_identifier", "") for r in dataset_results]
                top_match = len(truncated_ids) > 0 and truncated_ids[0] == expected_id
                any_match = expected_id in truncated_ids

                row = {
                    "paper_name": q["paper_name"],
                    "query": query_text,
                    "expected_identifier": expected_id,
                    "expected_identifier_type": q["expected_identifier_type"],
                    "predicted_results": json.dumps(dataset_results, default=str),
                    "top_match": top_match,
                    "any_match": any_match,
                    "tool_call_count": result.get("tool_call_count", 0),
                    "total_tokens": result.get("token_usage", {}).get("totals", {}).get("total_tokens", 0),
                    "number_of_identifiers_returned": len(truncated_ids),
                    "data_identifiers": ", ".join(truncated_ids),
                }

                # Flatten tool calls into rows for the Tool Calls sheet
                for idx, tc in enumerate(result.get("tool_calls", []), 1):
                    tc_rows.append({
                        "query": query_text,
                        "tool_call_index": idx,
                        "tool_id": tc.get("id", ""),
                        "tool_name": tc.get("name", ""),
                        "arguments": str(tc.get("arguments", "")),
                        "output": str(tc.get("output", "")),
                    })

                top_str = "TOP MATCH" if top_match else ("ANY MATCH" if any_match else "NO MATCH")
                print(f"  → [{i}/{len(pending)}] {top_str} | {len(dataset_results)} results returned")

            except Exception as e:
                print(f"  → [{i}/{len(pending)}] ERROR: {e}")
                row = {
                    "paper_name": q["paper_name"],
                    "query": query_text,
                    "expected_identifier": q["expected_identifier"],
                    "expected_identifier_type": q["expected_identifier_type"],
                    "predicted_results": json.dumps([{"error": str(e)}]),
                    "top_match": False,
                    "any_match": False,
                    "tool_call_count": 0,
                    "total_tokens": 0,
                    "number_of_identifiers_returned": 0,
                    "data_identifiers": "",
                }

            async with save_lock:
                results.append(row)
                all_tool_calls.extend(tc_rows)
                completed["count"] += 1
                save_results(results, all_tool_calls, output_path)

    tasks = [run_single(i, q) for i, q in enumerate(pending, 1)]
    await asyncio.gather(*tasks)

    # Final summary
    top_matches = sum(1 for r in results if r.get("top_match"))
    any_matches = sum(1 for r in results if r.get("any_match"))
    n = len(results)
    print(f"\nDone! Top match: {top_matches}/{n} ({top_matches/n*100:.1f}%) | Any match: {any_matches}/{n} ({any_matches/n*100:.1f}%)")
    print(f"Results saved to: {output_path}")



async def multi_batch_run(
    input_path: str,
    config_name: str,
    num_runs: int = 3,
    concurrency: int = 1,
    limit: int | None = None,
):
    """Run batch_run() multiple times independently, then report recall@k mean/std."""
    for run_id in range(1, num_runs + 1):
        print(f"\n{'=' * 60}")
        print(f"RUN {run_id}/{num_runs}")
        print(f"{'=' * 60}\n")
        await batch_run(input_path, config_name, concurrency, limit, run_id=run_id, fresh=True)

    # Import recall helpers (same sys.path already set up at module level)
    from calculate_top_k_recall import load_results, compute_top_k_recall

    max_k = 10
    recall_data: dict[int, list[float]] = {k: [] for k in range(1, max_k + 1)}

    for run_id in range(1, num_runs + 1):
        path = RESULTS_DIR / f"{config_name}_run{run_id}.xlsx"
        results = load_results(path)
        for k in range(1, max_k + 1):
            hits, total = compute_top_k_recall(results, k)
            recall_data[k].append(hits / total * 100 if total else 0.0)

    # Print summary table
    print(f"\n{'=' * 60}")
    print(f"Recall@k Summary ({num_runs} runs)")
    print(f"{'=' * 60}")
    print(f"{'k':<5} {'mean':>8} {'std':>8}  per-run values")
    print("-" * 60)

    summary: dict[str, dict] = {}
    for k in range(1, max_k + 1):
        values = recall_data[k]
        m = mean(values)
        s = stdev(values) if len(values) > 1 else 0.0
        summary[f"recall@{k}"] = {"mean": round(m, 2), "std": round(s, 2), "values": [round(v, 2) for v in values]}
        print(f"{k:<5} {m:>7.1f}% {s:>7.1f}%  {values}")

    summary_path = RESULTS_DIR / f"{config_name}_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary saved to: {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch runner for PDS agent configurations")
    parser.add_argument("--input", required=True, help="Path to input spreadsheet with queries")
    parser.add_argument("--config", required=True, choices=list(CONFIGS.keys()),
                        help="Agent configuration to use")
    parser.add_argument("--concurrency", type=int, default=1,
                        help="Number of queries to run in parallel (default: 1)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process the first N pending queries (e.g. --limit 2 for a quick debug run)")
    parser.add_argument("--num-runs", type=int, default=1,
                        help="Number of independent runs (default: 1). When >1, runs N times and reports recall@k mean/std.")
    args = parser.parse_args()

    if args.num_runs > 1:
        asyncio.run(multi_batch_run(args.input, args.config, num_runs=args.num_runs, concurrency=args.concurrency, limit=args.limit))
    else:
        asyncio.run(batch_run(args.input, args.config, concurrency=args.concurrency, limit=args.limit))
