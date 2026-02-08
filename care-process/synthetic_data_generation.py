from agents import HostedMCPTool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace, set_default_openai_client
from pydantic import BaseModel
from openai import AsyncOpenAI
from openai.types.shared.reasoning import Reasoning
from prompts import extraction_prompt, query_generation_prompt, consolidate_prompt
import dotenv
import os
import base64
import json

dotenv.load_dotenv()

# Configure OpenAI client with extended timeout for reasoning models
custom_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=1800.0  # 30 minutes for gpt-5.2 with high reasoning effort
)
set_default_openai_client(custom_client)


def extract_tool_calls_from_runner_result(runner_result) -> list[dict]:
    """Extract all tool calls and their results from a Runner result."""
    tool_calls = []

    # Iterate through all items in the runner result
    for item in runner_result.new_items:
        # Check if this item contains tool calls
        if hasattr(item, 'tool_calls') and item.tool_calls:
            for tc in item.tool_calls:
                tool_call_entry = {
                    'id': tc.id,
                    'name': tc.function.name,
                    'arguments': tc.function.arguments,
                    'result': None
                }

                # Find corresponding tool result
                for result_item in runner_result.new_items:
                    if hasattr(result_item, 'tool_call_id') and result_item.tool_call_id == tc.id:
                        tool_call_entry['result'] = result_item.content
                        break

                tool_calls.append(tool_call_entry)

    return tool_calls

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


class QueryGenerationAgentSchema__PdsMetadataFields(BaseModel):
  fields: list[str]


class QueryGenerationAgentSchema__ToolValidation(BaseModel):
  tools_used: list[str]
  constraints_summary: str
  initial_match_count: float
  final_match_count: float


class QueryGenerationAgentSchema__QueriesItem(BaseModel):
  query: str
  data_identifier: str
  data_identifier_type: str
  pds_metadata_fields: QueryGenerationAgentSchema__PdsMetadataFields
  tool_validation: QueryGenerationAgentSchema__ToolValidation


class QueryGenerationAgentSchema(BaseModel):
  paper_title: str
  queries: list[QueryGenerationAgentSchema__QueriesItem]


class ConsolidatedOutputAgentSchema__PdsMetadataFields(BaseModel):
  fields: list[str]


class ConsolidatedOutputAgentSchema__ToolValidation(BaseModel):
  tools_used: list[str]
  constraints_summary: str
  initial_match_count: float
  final_match_count: float


class ConsolidatedOutputAgentSchema__QueriesItem(BaseModel):
  query: str
  data_identifier: str
  data_identifier_type: str
  pds_metadata_fields: ConsolidatedOutputAgentSchema__PdsMetadataFields
  tool_validation: ConsolidatedOutputAgentSchema__ToolValidation


class ConsolidatedOutputAgentSchema(BaseModel):
  paper_title: str
  queries: list[ConsolidatedOutputAgentSchema__QueriesItem]


extraction_agent = Agent(
  name="Extraction Agent",
  instructions=extraction_prompt,
  model="gpt-5.2",
  output_type=ExtractionAgentSchema,
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="high",
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


consolidated_output_agent = Agent(
  name="Consolidated Output Agent",
  instructions= consolidate_prompt ,
  model="gpt-5.2",
  output_type=ConsolidatedOutputAgentSchema,
  model_settings=ModelSettings(
    store=True,
    reasoning=Reasoning(
      effort="low",
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
      "datasets": [

      ],
      "i": None,
      "results": [

      ]
    }
    workflow = workflow_input.model_dump()

    # Build content based on input type
    content = []
    if workflow["pdf_file_path"]:
      # Read and base64 encode the PDF file
      with open(workflow["pdf_file_path"], "rb") as pdf_file:
        pdf_bytes = pdf_file.read()
        b64_data = base64.b64encode(pdf_bytes).decode("utf-8")

      # Extract filename from path
      pdf_filename = os.path.basename(workflow["pdf_file_path"])

      content.append({
        "type": "input_file",
        "filename": pdf_filename,
        "file_data": f"data:application/pdf;base64,{b64_data}"
      })
      # Add instruction text
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
    extraction_agent_result_temp = await Runner.run(
      extraction_agent,
      input=[
        *conversation_history
      ],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_6985d21ad4ac819098cd28b61001ab0808e2db94f194d94c"
      })
    )
    extraction_agent_result = {
      "output_text": extraction_agent_result_temp.final_output.json(),
      "output_parsed": extraction_agent_result_temp.final_output.model_dump(),
      "tool_calls": extract_tool_calls_from_runner_result(extraction_agent_result_temp)
    }
    state["i"] = 0
    state["results"] = []
    state["query_generation_full_results"] = []  # Store full results with tool_calls
    state["datasets"] = extraction_agent_result["output_parsed"]["datasets"]
    while state["i"] < len(state["datasets"]):
      transform_result = {"dataset": state["datasets"][state["i"]]}
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
        "tool_calls": extract_tool_calls_from_runner_result(query_generation_agent_result_temp),
        "dataset_index": state["i"]
      }
      state["results"] = state["results"] + [query_generation_agent_result["output_parsed"]]
      state["query_generation_full_results"] = state["query_generation_full_results"] + [query_generation_agent_result]
      state["i"] = state["i"] + 1
    consolidated_output_agent_result_temp = await Runner.run(
      consolidated_output_agent,
      input=[
        {
          "role": "user",
          "content": [
            {
              "type": "input_text",
              "text": f"""here are the results:

            {state["results"]}"""
            }
          ]
        }
      ],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_6985d21ad4ac819098cd28b61001ab0808e2db94f194d94c"
      })
    )

    conversation_history.extend([item.to_input_item() for item in consolidated_output_agent_result_temp.new_items])

    consolidated_output_agent_result = {
      "output_text": consolidated_output_agent_result_temp.final_output.json(),
      "output_parsed": consolidated_output_agent_result_temp.final_output.model_dump(),
      "tool_calls": extract_tool_calls_from_runner_result(consolidated_output_agent_result_temp)
    }

    # Collect all tool calls across all agents
    all_tool_calls = []
    all_tool_calls.extend(extraction_agent_result.get("tool_calls", []))
    for qg_result in state["query_generation_full_results"]:
      all_tool_calls.extend(qg_result.get("tool_calls", []))
    all_tool_calls.extend(consolidated_output_agent_result.get("tool_calls", []))

    # Return comprehensive results from all agents
    return {
      "extraction_agent": extraction_agent_result,
      "query_generation_agent_results": state["query_generation_full_results"],  # Include full results with tool_calls
      "consolidated_output": consolidated_output_agent_result,
      "final_output": consolidated_output_agent_result["output_parsed"],
      "all_tool_calls": all_tool_calls,
      "tool_call_summary": {
        "total_tool_calls": len(all_tool_calls),
        "extraction_agent_calls": len(extraction_agent_result.get("tool_calls", [])),
        "query_generation_agent_calls": sum(len(r.get("tool_calls", [])) for r in state["query_generation_full_results"]),
        "consolidated_output_agent_calls": len(consolidated_output_agent_result.get("tool_calls", []))
      }
    }
