"""
Batch process all papers in a folder and output results to a spreadsheet.

Usage:
    uv run python care-process/batch_process_papers.py
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import os
import dotenv
import pandas as pd

# Load environment variables from .env file
dotenv.load_dotenv()

from synthetic_data_generation import run_workflow, WorkflowInput


# Configuration
PAPERS_FOLDER = Path("care-process/temp")
OUTPUT_FOLDER = Path("care-process/batch_results")
SPREADSHEET_PATH = OUTPUT_FOLDER / "results_spreadsheet.xlsx"
CSV_PATH = OUTPUT_FOLDER / "results_spreadsheet.csv"
TOOL_CALLS_CSV_PATH = OUTPUT_FOLDER / "tool_calls_detailed.csv"


async def process_single_paper(paper_path: Path) -> dict:
    """Process a single paper and return structured results."""
    print(f"\nProcessing: {paper_path.name}")
    print("="*80)

    try:
        # Pass the PDF file path to the workflow
        # The workflow will read and send the PDF content to the agent
        workflow_input = WorkflowInput(pdf_file_path=str(paper_path.absolute()))

        # Run workflow
        result = await run_workflow(workflow_input)

        # Extract key information for spreadsheet
        extraction_output = result["extraction_agent"]["output_parsed"]
        query_gen_outputs = result["query_generation_agent_results"]
        final_output = result["final_output"]

        num_datasets = len(extraction_output.get("datasets", []))
        num_queries = len(final_output.get("queries", []))

        # Extract tool call information
        all_tool_calls = result.get("all_tool_calls", [])
        tool_call_summary = result.get("tool_call_summary", {})

        paper_result = {
            "paper_name": paper_path.name,
            "status": "success",
            "num_datasets_extracted": num_datasets,
            "num_queries_generated": num_queries,
            "total_tool_calls": tool_call_summary.get("total_tool_calls", 0),
            "extraction_agent_tool_calls": tool_call_summary.get("extraction_agent_calls", 0),
            "query_generation_agent_tool_calls": tool_call_summary.get("query_generation_agent_calls", 0),
            "consolidated_output_agent_tool_calls": tool_call_summary.get("consolidated_output_agent_calls", 0),
            "extraction_output": json.dumps(extraction_output, indent=2),
            "query_generation_outputs": json.dumps(query_gen_outputs, indent=2),
            "final_output": json.dumps(final_output, indent=2),
            "all_tool_calls": json.dumps(all_tool_calls, indent=2),
            "paper_title": final_output.get("paper_title", "N/A"),
            "error": None,
            "timestamp": datetime.now().isoformat()
        }

        # Save individual JSON result
        individual_output = OUTPUT_FOLDER / "json" / f"{paper_path.stem}.json"
        individual_output.parent.mkdir(parents=True, exist_ok=True)
        with open(individual_output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        print(f"✓ Successfully processed: {paper_path.name}")
        print(f"  - Datasets extracted: {num_datasets}")
        print(f"  - Queries generated: {num_queries}")
        print(f"  - Total tool calls: {paper_result['total_tool_calls']}")

        return paper_result

    except Exception as e:
        print(f"✗ Error processing {paper_path.name}: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "paper_name": paper_path.name,
            "status": "error",
            "num_datasets_extracted": 0,
            "num_queries_generated": 0,
            "total_tool_calls": 0,
            "extraction_agent_tool_calls": 0,
            "query_generation_agent_tool_calls": 0,
            "consolidated_output_agent_tool_calls": 0,
            "extraction_output": None,
            "query_generation_outputs": None,
            "final_output": None,
            "all_tool_calls": None,
            "paper_title": None,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def main():
    print("="*80)
    print("PDS Dataset Benchmark Generation - Batch Processing")
    print("="*80)

    # Create output folder
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # Find all PDF files
    paper_files = list(PAPERS_FOLDER.glob("*.pdf"))

    if not paper_files:
        print(f"\nNo PDF files found in: {PAPERS_FOLDER}")
        return

    print(f"\nFound {len(paper_files)} papers to process:")
    for pf in paper_files:
        print(f"  - {pf.name}")

    # Load existing results if spreadsheet exists
    existing_papers = set()
    existing_results = []
    if SPREADSHEET_PATH.exists():
        print(f"\nLoading existing results from: {SPREADSHEET_PATH}")
        try:
            existing_df = pd.read_excel(SPREADSHEET_PATH, engine='openpyxl')
            existing_papers = set(existing_df['paper_name'].tolist())
            existing_results = existing_df.to_dict('records')
            print(f"Found {len(existing_papers)} already processed papers")
        except Exception as e:
            print(f"Warning: Could not load existing spreadsheet: {e}")
            print("Will start fresh.")

    # Filter out already processed papers
    papers_to_process = [pf for pf in paper_files if pf.name not in existing_papers]
    skipped_count = len(paper_files) - len(papers_to_process)

    if skipped_count > 0:
        print(f"\nSkipping {skipped_count} already processed papers:")
        for pf in paper_files:
            if pf.name in existing_papers:
                print(f"  - {pf.name} (already exists)")

    if not papers_to_process:
        print("\n" + "="*80)
        print("All papers have already been processed. Nothing to do.")
        print("="*80)
        return

    print("\n" + "="*80)
    print(f"Starting parallel processing of {len(papers_to_process)} new papers...")
    print("="*80)

    # Process papers in parallel
    print("\nProcessing all papers concurrently...")
    tasks = [process_single_paper(paper_path) for paper_path in papers_to_process]
    new_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine with existing results
    results = existing_results.copy()
    for result in new_results:
        if isinstance(result, Exception):
            print(f"\n✗ Unexpected error: {result}")
        else:
            results.append(result)

    # Create DataFrame
    df = pd.DataFrame(results)

    # Reorder columns for better readability
    column_order = [
        "paper_name",
        "status",
        "paper_title",
        "num_datasets_extracted",
        "num_queries_generated",
        "total_tool_calls",
        "extraction_agent_tool_calls",
        "query_generation_agent_tool_calls",
        "consolidated_output_agent_tool_calls",
        "extraction_output",
        "query_generation_outputs",
        "final_output",
        "all_tool_calls",
        "error",
        "timestamp"
    ]
    df = df[column_order]

    # Save to Excel
    print("\n" + "="*80)
    print("Saving results to spreadsheet...")
    print("="*80)

    df.to_excel(SPREADSHEET_PATH, index=False, engine='openpyxl')
    print(f"✓ Excel saved to: {SPREADSHEET_PATH}")

    # Save to CSV as well
    df.to_csv(CSV_PATH, index=False)
    print(f"✓ CSV saved to: {CSV_PATH}")

    # Create detailed tool calls CSV
    tool_calls_rows = []
    for result in results:
        if result.get("all_tool_calls"):
            try:
                tool_calls = json.loads(result["all_tool_calls"]) if isinstance(result["all_tool_calls"], str) else result["all_tool_calls"]
                for tc in tool_calls:
                    tool_calls_rows.append({
                        "paper_name": result["paper_name"],
                        "tool_call_id": tc.get("id", ""),
                        "tool_name": tc.get("name", ""),
                        "arguments": tc.get("arguments", ""),
                        "result": tc.get("result", "")
                    })
            except Exception as e:
                print(f"Warning: Could not parse tool calls for {result['paper_name']}: {e}")

    if tool_calls_rows:
        tool_calls_df = pd.DataFrame(tool_calls_rows)
        tool_calls_df.to_csv(TOOL_CALLS_CSV_PATH, index=False)
        print(f"✓ Tool calls CSV saved to: {TOOL_CALLS_CSV_PATH}")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total papers in spreadsheet: {len(results)}")
    print(f"Previously processed: {len(existing_results)}")
    print(f"Newly processed: {len(results) - len(existing_results)}")
    print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"Errors: {sum(1 for r in results if r['status'] == 'error')}")
    print(f"Total datasets extracted: {sum(r.get('num_datasets_extracted', 0) for r in results)}")
    print(f"Total queries generated: {sum(r.get('num_queries_generated', 0) for r in results)}")
    print(f"Total tool calls made: {sum(r.get('total_tool_calls', 0) for r in results)}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
