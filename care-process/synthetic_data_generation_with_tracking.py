from agents import Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace, set_default_openai_client
from pydantic import BaseModel
from openai import AsyncOpenAI
from openai.types.shared.reasoning import Reasoning
from prompts import extraction_prompt, query_generation_prompt
from utils import make_mcp_tool, extract_tool_calls_with_outputs, extract_token_usage, aggregate_token_usage
from loguru import logger
import dotenv
import os
import base64

dotenv.load_dotenv()

# Configure OpenAI client with extended timeout for reasoning models
custom_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=1800.0  # 30 minutes for gpt-5.2 with high reasoning effort
)
set_default_openai_client(custom_client)

# Tool definitions
mcp = make_mcp_tool()


class ExtractionAgentSchema__DatasetsItem(BaseModel):
  pds_dataset_product_name: str
  mission_project: str
  instrument_sensor: str
  instrument_host_spacecraft: str
  target_name: str
  target_type: str
  small_body_designations: str
  measurement_observable: str
  wavelength_bandpass: str
  data_type_product_type: str
  acquisition_date_time_range: str
  location_coverage: str
  spatial_resolution: str
  temporal_resolution_cadence: str
  processing_level_calibration_level: str
  pds_identifiers: str
  how_used: str


class ExtractionAgentSchema(BaseModel):
  datasets: list[ExtractionAgentSchema__DatasetsItem]


class QueryGenerationAgentSchema__QueriesItem(BaseModel):
  query: str
  data_identifier: str
  data_identifier_type: str


class QueryGenerationAgentSchema(BaseModel):
  paper_title: str
  queries: list[QueryGenerationAgentSchema__QueriesItem]


extraction_agent = Agent(
  name="Extraction Agent",
  instructions=extraction_prompt,
  model="gpt-5.2",
  output_type=ExtractionAgentSchema,
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="medium",
      summary="auto"
    )
  )
)


query_generation_agent = Agent(
  name="Query Generation Agent",
  instructions=query_generation_prompt,
  model="gpt-5.2",
  tools=[
    mcp
  ],
  output_type=QueryGenerationAgentSchema,
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="high",
      summary="auto"
    )
  )
)


class WorkflowInput(BaseModel):
  input_as_text: str | None = None
  pdf_file_path: str | None = None


# Main code entrypoint
async def run_workflow(workflow_input: WorkflowInput):
  with trace("PDS Dataset Benchmark Generation agent [Simran]"):
    state = {
      "datasets": [],
      "i": None,
      "results": []
    }
    workflow = workflow_input.model_dump()

    # Build content based on input type
    content = []
    if workflow["pdf_file_path"]:
      with open(workflow["pdf_file_path"], "rb") as pdf_file:
        pdf_bytes = pdf_file.read()
        b64_data = base64.b64encode(pdf_bytes).decode("utf-8")

      pdf_filename = os.path.basename(workflow["pdf_file_path"])

      content.append({
        "type": "input_file",
        "filename": pdf_filename,
        "file_data": f"data:application/pdf;base64,{b64_data}"
      })
      content.append({
        "type": "input_text",
        "text": "Please analyze this PDF file and extract the PDS dataset information."
      })
    elif workflow["input_as_text"]:
      content.append({
        "type": "input_text",
        "text": workflow["input_as_text"]
      })

    conversation_history: list[TResponseInputItem] = [
      {
        "role": "user",
        "content": content
      }
    ]

    # --- Extraction Agent ---
    pdf_label = os.path.basename(workflow.get("pdf_file_path", "")) or "text input"
    logger.info("[Extraction Agent] Starting extraction for: {}", pdf_label)
    extraction_agent_result_temp = await Runner.run(
      extraction_agent,
      input=[*conversation_history],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_6985d21ad4ac819098cd28b61001ab0808e2db94f194d94c"
      })
    )
    extraction_agent_result = {
      "output_text": extraction_agent_result_temp.final_output.json(),
      "output_parsed": extraction_agent_result_temp.final_output.model_dump(),
      "token_usage": extract_token_usage(extraction_agent_result_temp),
    }

    extraction_tokens = extraction_agent_result["token_usage"]["totals"]
    logger.info(
      "[Extraction Agent] Completed | datasets extracted: {} | tokens: {} input, {} output ({} reasoning)",
      len(extraction_agent_result["output_parsed"]["datasets"]),
      extraction_tokens["input_tokens"],
      extraction_tokens["output_tokens"],
      extraction_tokens["reasoning_tokens"],
    )
    for i, ds in enumerate(extraction_agent_result["output_parsed"]["datasets"]):
      logger.debug(
        "[Extraction Agent] Dataset {}: {} | mission={} | instrument={}",
        i, ds.get("pds_dataset_product_name", "N/A"), ds.get("mission_project", "N/A"), ds.get("instrument_sensor", "N/A"),
      )

    state["i"] = 0
    state["results"] = []
    state["query_generation_full_results"] = []
    state["datasets"] = extraction_agent_result["output_parsed"]["datasets"]

    # --- Query Generation Agent (per dataset) ---
    num_datasets = len(state["datasets"])
    while state["i"] < num_datasets:
      dataset_idx = state["i"]
      transform_result = {"dataset": state["datasets"][dataset_idx]}
      dataset_name = transform_result["dataset"].get("pds_dataset_product_name", f"dataset_{dataset_idx}")
      logger.info("[Query Generation Agent] Processing dataset {}/{}: {}", dataset_idx + 1, num_datasets, dataset_name)

      query_generation_agent_result_temp = await Runner.run(
        query_generation_agent,
        input=[
          *conversation_history,
          {
            "role": "user",
            "content": [
              {
                "type": "input_text",
                "text": f"""here is the extracted metadata you need to work with

              {transform_result["dataset"]}
              """
              }
            ]
          }
        ],
        run_config=RunConfig(trace_metadata={
          "__trace_source__": "agent-builder",
          "workflow_id": "wf_6985d21ad4ac819098cd28b61001ab0808e2db94f194d94c"
        })
      )
      query_generation_agent_result = {
        "output_text": query_generation_agent_result_temp.final_output.json(),
        "output_parsed": query_generation_agent_result_temp.final_output.model_dump(),
        "tool_calls": extract_tool_calls_with_outputs(query_generation_agent_result_temp),
        "token_usage": extract_token_usage(query_generation_agent_result_temp),
        "dataset_index": dataset_idx
      }

      qg_tokens = query_generation_agent_result["token_usage"]["totals"]
      qg_queries = query_generation_agent_result["output_parsed"].get("queries", [])
      qg_tool_calls = query_generation_agent_result["tool_calls"]
      logger.info(
        "[Query Generation Agent] Dataset {}/{} done | queries: {} | tool calls: {} | tokens: {} input, {} output ({} reasoning)",
        dataset_idx + 1, num_datasets, len(qg_queries), len(qg_tool_calls),
        qg_tokens["input_tokens"], qg_tokens["output_tokens"], qg_tokens["reasoning_tokens"],
      )
      for tc in qg_tool_calls:
        logger.debug("[Query Generation Agent] Tool call: {} (id={})", tc["name"], tc["id"])
      for q in qg_queries:
        logger.debug(
          "[Query Generation Agent] Query: '{}' -> {} ({})",
          q["query"][:100], q["data_identifier"], q["data_identifier_type"],
        )

      state["results"] = state["results"] + [query_generation_agent_result["output_parsed"]]
      state["query_generation_full_results"] = state["query_generation_full_results"] + [query_generation_agent_result]
      state["i"] = state["i"] + 1

    # --- Consolidate results (no LLM call needed) ---
    logger.info("[Consolidation] Merging results from {} datasets", num_datasets)
    all_tool_calls = []
    final_queries = []
    for qg_result in state["query_generation_full_results"]:
      all_tool_calls.extend(qg_result["tool_calls"])
      for q in qg_result["output_parsed"].get("queries", []):
        final_queries.append({
          "query": q["query"],
          "data_identifier": q["data_identifier"],
          "data_identifier_type": q["data_identifier_type"],
        })

    # --- Aggregate token usage ---
    all_token_usages = [extraction_agent_result["token_usage"]]
    for qg_result in state["query_generation_full_results"]:
      all_token_usages.append(qg_result["token_usage"])
    total_token_usage = aggregate_token_usage(all_token_usages)

    logger.info(
      "[Workflow Complete] {} | total queries: {} | total tool calls: {} | total tokens: {} (input={}, output={}, reasoning={})",
      pdf_label, len(final_queries), len(all_tool_calls),
      total_token_usage["total_tokens"], total_token_usage["input_tokens"],
      total_token_usage["output_tokens"], total_token_usage["reasoning_tokens"],
    )

    return {
      "extraction_agent": extraction_agent_result,
      "query_generation_agent_results": state["query_generation_full_results"],
      "final_output": final_queries,
      "all_tool_calls": all_tool_calls,
      "tool_call_summary": {
        "total_tool_calls": len(all_tool_calls),
        "query_generation_agent_calls": sum(len(r["tool_calls"]) for r in state["query_generation_full_results"]),
      },
      "token_usage": {
        "extraction_agent": extraction_agent_result["token_usage"],
        "query_generation_agents": [r["token_usage"] for r in state["query_generation_full_results"]],
        "totals": total_token_usage,
      }
    }
