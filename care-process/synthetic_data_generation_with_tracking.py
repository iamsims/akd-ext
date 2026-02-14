from agents import HostedMCPTool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace, set_default_openai_client
from agents.items import ToolCallItem, ToolCallOutputItem
from pydantic import BaseModel
from openai import AsyncOpenAI
from openai.types.shared.reasoning import Reasoning
from prompts import extraction_prompt, query_generation_prompt
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


def extract_tool_calls_with_outputs(runner_result) -> list[dict]:
    """Extract tool calls paired with their outputs from the runner result."""
    # Build a map of call_id -> output from ToolCallOutputItems (for function tools)
    output_map: dict[str, str] = {}
    for item in runner_result.new_items:
        if isinstance(item, ToolCallOutputItem):
            raw = item.raw_item
            call_id = getattr(raw, "call_id", None) or getattr(raw, "tool_call_id", None)
            if call_id:
                output_map[call_id] = item.output

    # Walk ToolCallItems and pair with outputs
    tool_calls = []
    for item in runner_result.new_items:
        if isinstance(item, ToolCallItem):
            raw = item.raw_item
            call_id = getattr(raw, "id", None) or getattr(raw, "call_id", None)
            name = getattr(raw, "name", None) or getattr(getattr(raw, "function", None), "name", None)
            arguments = getattr(raw, "arguments", None) or getattr(getattr(raw, "function", None), "arguments", None)
            # For MCP tools, the output lives directly on the McpCall object.
            # For function tools, it's in the separate ToolCallOutputItem map.
            output = getattr(raw, "output", None) or output_map.get(call_id)

            tool_calls.append({
                "id": call_id,
                "name": name,
                "arguments": arguments,
                "output": output,
            })
    return tool_calls


def extract_token_usage(runner_result) -> dict:
    """Extract per-response and total token usage from raw_responses."""
    per_response = []
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "reasoning_tokens": 0, "cached_tokens": 0}

    for resp in runner_result.raw_responses:
        usage = resp.usage
        reasoning = getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", 0) or 0
        cached = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", 0) or 0
        entry = {
            "response_id": resp.response_id,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "reasoning_tokens": reasoning,
            "cached_tokens": cached,
        }
        per_response.append(entry)
        totals["input_tokens"] += usage.input_tokens
        totals["output_tokens"] += usage.output_tokens
        totals["total_tokens"] += usage.total_tokens
        totals["reasoning_tokens"] += reasoning
        totals["cached_tokens"] += cached

    return {"per_response": per_response, "totals": totals}


def aggregate_token_usage(usages: list[dict]) -> dict:
    """Aggregate multiple token_usage dicts into a single totals dict."""
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "reasoning_tokens": 0, "cached_tokens": 0}
    for u in usages:
        for key in totals:
            totals[key] += u["totals"][key]
    return totals


# Tool definitions
mcp = HostedMCPTool(tool_config={
  "type": "mcp",
  "server_label": "pds_mcp_server",
  "server_url": "https://complex-chocolate-python.fastmcp.app/mcp",
  "authorization": os.getenv("FAST_MCP_AUTH"),
  "allowed_tools": [
    "img_count_products_tool",
    "img_get_facets_tool",
    "img_get_product_tool",
    "img_search_products_tool",
    "ode_count_products_tool",
    "ode_get_feature_bounds_tool",
    "ode_list_feature_classes_tool",
    "ode_list_feature_names_tool",
    "ode_list_instruments_tool",
    "ode_search_products_tool",
    "opus_count_observations_tool",
    "opus_get_fields_tool",
    "opus_get_files_tool",
    "opus_get_metadata_tool",
    "opus_search_observations_tool",
    "pds4get_collection_products_tool",
    "pds4search_bundles_tool",
    "pds4search_collections_tool",
    "pds4search_instrument_hosts_tool",
    "pds4search_instruments_tool",
    "pds4search_investigations_tool",
    "pds4search_observational_tool",
    "pds4search_products_advanced_tool",
    "pds4search_targets_tool",
    "pds_catalog_get_dataset_tool",
    "pds_catalog_get_stats_tool",
    "pds_catalog_list_missions_tool",
    "pds_catalog_list_targets_tool",
    "pds_catalog_search_tool",
    "sbn_list_sources_tool",
    "sbn_search_fixed_target_tool",
    "sbn_search_moving_target_tool"
  ],
  "require_approval": "never"
})


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
