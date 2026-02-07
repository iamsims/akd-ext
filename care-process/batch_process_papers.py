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
PAPERS_FOLDER = Path("care-process/Synthetic data papers")
OUTPUT_FOLDER = Path("care-process/batch_results")
SPREADSHEET_PATH = OUTPUT_FOLDER / "results_spreadsheet.xlsx"
CSV_PATH = OUTPUT_FOLDER / "results_spreadsheet.csv"


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

        paper_result = {
            "paper_name": paper_path.name,
            "status": "success",
            "num_datasets_extracted": num_datasets,
            "num_queries_generated": num_queries,
            "extraction_output": json.dumps(extraction_output, indent=2),
            "query_generation_outputs": json.dumps(query_gen_outputs, indent=2),
            "final_output": json.dumps(final_output, indent=2),
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
            "extraction_output": None,
            "query_generation_outputs": None,
            "final_output": None,
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

    print("\n" + "="*80)
    print("Starting processing...")
    print("="*80)

    # Process all papers
    results = []
    for i, paper_path in enumerate(paper_files, 1):
        print(f"\n[{i}/{len(paper_files)}]", end=" ")
        result = await process_single_paper(paper_path)
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
        "extraction_output",
        "query_generation_outputs",
        "final_output",
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

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total papers processed: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"Errors: {sum(1 for r in results if r['status'] == 'error')}")
    print(f"Total datasets extracted: {sum(r['num_datasets_extracted'] for r in results)}")
    print(f"Total queries generated: {sum(r['num_queries_generated'] for r in results)}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
