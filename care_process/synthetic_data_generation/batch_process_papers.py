"""
Batch process all papers in a folder and output results to a spreadsheet.

Uses synthetic_data_generation_with_tracking which includes token usage tracking
and removes the consolidated output agent (consolidation done in Python).

Each run gets a unique timestamp ID. Structure:
    batch_results/run_<timestamp>/
        results/   -> results_spreadsheet.xlsx, results_spreadsheet.csv
        outputs/   -> individual JSON full outputs per paper

Spreadsheet format (one row per query, not per paper):
    paper_name | query | data_identifier | data_identifier_type

Usage:
    uv run python care-process/batch_process_papers.py            # fresh run
    uv run python care-process/batch_process_papers.py --resume   # resume most recent run
"""

import argparse
import asyncio
import json
from pathlib import Path
from datetime import datetime
import dotenv
import pandas as pd
from loguru import logger

# Load environment variables from .env file
dotenv.load_dotenv()

from .synthetic_data_generation_with_tracking import run_workflow, WorkflowInput


# Configuration
PAPERS_FOLDER = Path("care_process/data")
BATCH_RESULTS_ROOT = Path("care_process/batch_results")


def find_most_recent_run() -> Path | None:
    """Find the most recent run_* folder by name (timestamp-sorted)."""
    if not BATCH_RESULTS_ROOT.exists():
        return None
    run_folders = sorted(
        [d for d in BATCH_RESULTS_ROOT.iterdir() if d.is_dir() and d.name.startswith("run_")],
        key=lambda d: d.name,
        reverse=True
    )
    return run_folders[0] if run_folders else None


async def process_single_paper(paper_path: Path, outputs_folder: Path) -> list[dict]:
    """Process a single paper and return a list of query rows for the spreadsheet."""
    logger.info("Processing: {}", paper_path.name)

    try:
        workflow_input = WorkflowInput(pdf_file_path=str(paper_path.absolute()))
        result = await run_workflow(workflow_input)

        # Save full JSON output
        individual_output = outputs_folder / f"{paper_path.stem}.json"
        with open(individual_output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        logger.debug("Saved full output to {}", individual_output)

        # Build one row per query
        final_output = result["final_output"]  # flat list of query dicts
        rows = []
        for q in final_output:
            rows.append({
                "paper_name": paper_path.name,
                "query": q["query"],
                "data_identifier": q["data_identifier"],
                "data_identifier_type": q["data_identifier_type"],
            })

        token_totals = result.get("token_usage", {}).get("totals", {})
        logger.success(
            "Finished: {} | {} queries | {} tool calls | {} total tokens",
            paper_path.name, len(rows),
            result.get("tool_call_summary", {}).get("total_tool_calls", 0),
            token_totals.get("total_tokens", "N/A"),
        )
        return rows

    except Exception as e:
        logger.exception("Error processing {}", paper_path.name)

        return [{
            "paper_name": paper_path.name,
            "query": None,
            "data_identifier": None,
            "data_identifier_type": f"ERROR: {e}",
        }]


def save_results(rows: list[dict], spreadsheet_path: Path, csv_path: Path):
    """Save query rows to Excel and CSV."""
    df = pd.DataFrame(rows, columns=["paper_name", "query", "data_identifier", "data_identifier_type"])

    df.to_excel(spreadsheet_path, index=False, engine='openpyxl')
    logger.success("Excel saved to: {}", spreadsheet_path)

    df.to_csv(csv_path, index=False)
    logger.success("CSV saved to: {}", csv_path)


def setup_run(paper_files: list[Path], resume: bool) -> tuple[Path, Path, Path, Path, list[Path], list[dict]]:
    """Set up run folder and determine which papers to process.

    Returns (run_folder, outputs_folder, spreadsheet_path, csv_path, papers_to_process, existing_rows).
    """
    existing_rows: list[dict] = []

    if resume:
        run_folder = find_most_recent_run()
        if run_folder is None:
            logger.warning("No existing runs found to resume. Starting a fresh run instead.")
            resume = False

    if not resume:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_folder = BATCH_RESULTS_ROOT / f"run_{run_id}"

    results_folder = run_folder / "results"
    outputs_folder = run_folder / "outputs"
    results_folder.mkdir(parents=True, exist_ok=True)
    outputs_folder.mkdir(parents=True, exist_ok=True)

    spreadsheet_path = results_folder / "results_spreadsheet.xlsx"
    csv_path = results_folder / "results_spreadsheet.csv"

    if resume and spreadsheet_path.exists():
        try:
            existing_df = pd.read_excel(spreadsheet_path, engine='openpyxl')
            existing_rows = existing_df.to_dict('records')
            done_papers = set(existing_df['paper_name'].unique())
        except Exception as e:
            logger.warning("Could not load existing spreadsheet: {}", e)
            done_papers = set()
    else:
        done_papers = set()

    papers_to_process = [pf for pf in paper_files if pf.name not in done_papers]
    return run_folder, outputs_folder, spreadsheet_path, csv_path, papers_to_process, existing_rows


async def main():
    parser = argparse.ArgumentParser(description="Batch process papers for PDS benchmark generation")
    parser.add_argument("--resume", action="store_true", help="Resume the most recent run, skipping already processed papers")
    args = parser.parse_args()

    paper_files = list(PAPERS_FOLDER.glob("*.pdf"))
    if not paper_files:
        logger.warning("No PDF files found in: {}", PAPERS_FOLDER)
        return

    run_folder, outputs_folder, spreadsheet_path, csv_path, papers_to_process, existing_rows = setup_run(
        paper_files, args.resume
    )

    # Add a file sink for this run (DEBUG level captures everything)
    logger.add(run_folder / "run.log", level="DEBUG")

    run_id = run_folder.name.removeprefix("run_")
    mode = "Resuming" if args.resume else "Batch Processing"

    logger.info("PDS Dataset Benchmark Generation - {} (Run {})", mode, run_id)
    logger.info("Output: {}", run_folder)

    if existing_rows:
        logger.info(
            "Found {} total papers, {} already processed",
            len(paper_files), len(paper_files) - len(papers_to_process),
        )

    if not papers_to_process:
        logger.info("All papers have already been processed. Nothing to do.")
        return

    logger.info("Processing {} papers:", len(papers_to_process))
    for pf in papers_to_process:
        logger.info("  - {}", pf.name)

    logger.info("Starting concurrent processing...")

    tasks = [process_single_paper(p, outputs_folder) for p in papers_to_process]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_rows = existing_rows.copy()
    for result in results:
        if isinstance(result, Exception):
            logger.error("Unexpected error: {}", result)
        else:
            all_rows.extend(result)

    logger.info("Saving results...")
    save_results(all_rows, spreadsheet_path, csv_path)


if __name__ == "__main__":
    asyncio.run(main())
