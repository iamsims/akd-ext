"""
Runner script for the PDS Dataset Benchmark Generation workflow.

Usage:
    uv run python care-process/run_workflow.py --input "path/to/paper.pdf"
    or
    uv run python care-process/run_workflow.py --text "Your research paper text here..."
"""

import asyncio
import json
import argparse
from pathlib import Path
from synthetic_data_generation import run_workflow, WorkflowInput


async def main():
    parser = argparse.ArgumentParser(
        description="Run PDS Dataset Benchmark Generation workflow"
    )

    # Input options - either file or text
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input",
        "-i",
        type=str,
        help="Path to input file (PDF or text file containing research paper)"
    )
    
    input_group.add_argument(
        "--text",
        "-t",
        type=str,
        help="Direct text input (research paper content)"
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output.json",
        help="Path to output JSON file (default: output.json)"
    )

    args = parser.parse_args()

    # Prepare input text
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file not found: {args.input}")
            return

        # Read the file
        if input_path.suffix.lower() == ".pdf":
            # For PDF files, you might need additional processing
            # For now, we'll just read as text (you may need to add PDF parsing)
            print("Warning: PDF parsing not implemented. Reading as text file.")
            input_text = input_path.read_text(encoding="utf-8")
        else:
            input_text = input_path.read_text(encoding="utf-8")

        print(f"Loaded input from: {args.input}")
        print(f"Input length: {len(input_text)} characters")
    else:
        input_text = args.text
        print(f"Using direct text input ({len(input_text)} characters)")

    # Create workflow input
    workflow_input = WorkflowInput(input_as_text=input_text)

    # Run the workflow
    print("\n" + "="*60)
    print("Starting PDS Dataset Benchmark Generation Workflow")
    print("="*60 + "\n")

    try:
        result = await run_workflow(workflow_input)

        # Save output to file
        output_path = Path(args.output)

        # The result should contain all agent outputs
        if result:
            # Save full results including intermediate outputs
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)

            print("\n" + "="*60)
            print(f"Workflow completed successfully!")
            print("="*60)
            print(f"\nResults Summary:")
            print(f"  - Datasets extracted: {len(result['extraction_agent']['output_parsed']['datasets'])}")
            print(f"  - Query generation runs: {len(result['query_generation_agent_results'])}")
            print(f"  - Final queries generated: {len(result['final_output']['queries'])}")
            print(f"\nAll results saved to: {output_path}")
            print("="*60)
        else:
            print("\nWarning: Workflow completed but returned no result")

    except Exception as e:
        print(f"\nError running workflow: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    asyncio.run(main())
