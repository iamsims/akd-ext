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
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# Ensure care-process is on sys.path so `utils` and `agent_run` imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_run.simple_agent_with_tools import run, AgentConfig
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
}

RESULTS_DIR = Path(__file__).resolve().parent / "batch_results" / "v2" / "tests"



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
        "predicted_results",
        "top_match", "any_match", "tool_call_count", "total_tokens",
    ]

    # Header styling
    header_font = Font(bold=True)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Data rows
    match_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    no_match_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    for row_idx, result in enumerate(results, 2):
        for col_idx, key in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=result.get(key))
            if key == "top_match":
                cell.fill = match_fill if result.get(key) else no_match_fill
            elif key == "any_match":
                cell.fill = match_fill if result.get(key) else no_match_fill

    # Summary row
    summary_row = len(results) + 3
    top_matches = sum(1 for r in results if r.get("top_match"))
    any_matches = sum(1 for r in results if r.get("any_match"))
    total_queries = len(results)
    total_tokens = sum(int(r.get("total_tokens", 0) or 0) for r in results)

    ws.cell(row=summary_row, column=1, value="SUMMARY").font = Font(bold=True)
    if total_queries:
        ws.cell(row=summary_row, column=2, value=f"Top match: {top_matches}/{total_queries} ({top_matches/total_queries*100:.1f}%) | Any match: {any_matches}/{total_queries} ({any_matches/total_queries*100:.1f}%)")
    else:
        ws.cell(row=summary_row, column=2, value="N/A")
    ws.cell(row=summary_row, column=9, value=f"Total tokens: {total_tokens:,}")

    # Column widths
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 60
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["E"].width = 80
    ws.column_dimensions["F"].width = 15
    ws.column_dimensions["G"].width = 15

    # --- Tool Calls sheet ---
    tc_ws = wb.create_sheet("Tool Calls")
    tc_headers = ["query", "tool_call_index", "tool_id", "tool_name", "arguments", "output"]
    for col, header in enumerate(tc_headers, 1):
        cell = tc_ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row_idx, tc in enumerate(all_tool_calls, 2):
        for col_idx, key in enumerate(tc_headers, 1):
            tc_ws.cell(row=row_idx, column=col_idx, value=tc.get(key))

    tc_ws.column_dimensions["A"].width = 60
    tc_ws.column_dimensions["D"].width = 30
    tc_ws.column_dimensions["E"].width = 60
    tc_ws.column_dimensions["F"].width = 80

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)


async def batch_run(input_path: str, config_name: str, concurrency: int = 1, limit: int | None = None):
    config = CONFIGS[config_name]
    queries = load_queries(input_path)
    output_path = RESULTS_DIR / f"{config_name}.xlsx"

    # Resume support
    already_done = load_existing_results(output_path)
    if already_done:
        print(f"Resuming: {len(already_done)} queries already processed, skipping them.")

    # Load existing results to preserve them
    results: list[dict] = []
    all_tool_calls: list[dict] = []
    if output_path.exists():
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

                # Check matches
                expected_id = q["expected_identifier"]
                all_predicted_ids = [r.get("data_identifier", "") for r in dataset_results]
                top_match = len(all_predicted_ids) > 0 and all_predicted_ids[0] == expected_id
                any_match = expected_id in all_predicted_ids

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



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch runner for PDS agent configurations")
    parser.add_argument("--input", required=True, help="Path to input spreadsheet with queries")
    parser.add_argument("--config", required=True, choices=list(CONFIGS.keys()),
                        help="Agent configuration to use")
    parser.add_argument("--concurrency", type=int, default=1,
                        help="Number of queries to run in parallel (default: 1)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process the first N pending queries (e.g. --limit 2 for a quick debug run)")
    args = parser.parse_args()

    asyncio.run(batch_run(args.input, args.config, concurrency=args.concurrency, limit=args.limit))
