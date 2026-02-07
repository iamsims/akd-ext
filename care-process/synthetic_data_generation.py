from agents import HostedMCPTool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig, trace
from pydantic import BaseModel
from openai.types.shared.reasoning import Reasoning
from prompts import extraction_prompt, query_generation_prompt, consolidate_prompt
import dotenv
import os

dotenv.load_dotenv()


# Tool definitions
mcp = HostedMCPTool(tool_config={
  "type": "mcp",
  "server_label": "pds_mcp_server",
  "server_url": "https://complex-chocolate-python.fastmcp.app/mcp",
  "authorization": os.getenv("FAST_MCP_AUTH"),
  "allowed_tools": [

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
  match_count: float


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
  match_count: float


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
      content.append({
        "type": "input_file",
        "input_file": {
          "data": open(workflow["pdf_file_path"], "rb").read(),
          "mime_type": "application/pdf"
        }
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
      "output_parsed": extraction_agent_result_temp.final_output.model_dump()
    }
    state["i"] = 0
    state["results"] = []
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
        "output_parsed": query_generation_agent_result_temp.final_output.model_dump()
      }
      state["results"] = state["results"] + [query_generation_agent_result["output_parsed"]]
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
      "output_parsed": consolidated_output_agent_result_temp.final_output.model_dump()
    }

    # Return comprehensive results from all agents
    return {
      "extraction_agent": extraction_agent_result,
      "query_generation_agent_results": state["results"],
      "consolidated_output": consolidated_output_agent_result,
      "final_output": consolidated_output_agent_result["output_parsed"]
    }
