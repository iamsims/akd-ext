from agents import HostedMCPTool, Agent, ModelSettings, Runner, RunConfig, trace, set_default_openai_client
from agents.items import ToolCallItem, ToolCallOutputItem
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from openai.types.shared.reasoning import Reasoning
import dotenv
import os
import json

dotenv.load_dotenv()

# Configure OpenAI client with extended timeout for reasoning models
custom_client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=1800.0
)
set_default_openai_client(custom_client)


def extract_tool_calls_with_outputs(runner_result) -> list[dict]:
    """Extract tool calls paired with their outputs from the runner result."""
    # Build a map of call_id -> output from ToolCallOutputItems
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


# MCP tool definition — same hosted server and tools as before
mcp = HostedMCPTool(tool_config={
    "type": "mcp",
    "server_label": "pds_mcp_server",
    "server_url": "https://complex-chocolate-python.fastmcp.app/mcp",
    "authorization": os.getenv("FAST_MCP_AUTH"),
    "allowed_tools": [
        "pds4crawl_context_product_tool",
        "pds4get_product_tool",
        "pds4search_bundles_tool",
        "pds4search_collections_tool",
        "pds4search_instrument_hosts_tool",
        "pds4search_instruments_tool",
        "pds4search_investigations_tool",
        "pds4search_products_tool",
        "pds4search_targets_tool",
        "pds_catalog_get_dataset_tool",
        "pds_catalog_list_missions_tool",
        "pds_catalog_list_targets_tool",
        "pds_catalog_search_tool",
        "pds_catalog_stats_tool",
        "ode_count_products_tool",
        "ode_get_feature_bounds_tool",
        "ode_list_feature_classes_tool",
        "ode_list_feature_names_tool",
        "ode_list_instruments_tool",
        "ode_search_products_tool",
        "opus_count_tool",
        "opus_get_files_tool",
        "opus_get_metadata_tool",
        "opus_search_tool",
        "img_count_tool",
        "img_get_facets_tool",
        "img_get_product_tool",
        "img_search_tool",
        "sbn_list_sources_tool",
        "sbn_search_coordinates_tool",
        "sbn_search_object_tool"
    ],
    "require_approval": "never"
})


SYSTEM_PROMPT = """You are a Planetary Data System (PDS) dataset discovery agent.

Given a natural-language query from a user, use the available MCP tools to find the
matching PDS dataset and return its identifier.

STRATEGY
1. Parse the query to identify key constraints: mission, instrument, target, time range,
   product type, processing level, spatial/spectral parameters, etc.
2. Choose the right MCP tools based on the PDS node mapping:
   - GEO node → ode_* tools
   - IMG node → img_* tools
   - RMS node → opus_* tools
   - SBN node → sbn_* tools
   - PPI / ATM nodes → pds4* / pds_catalog_* tools
   - Cross-node / catch-all → pds4search_*, pds_catalog_search_tool
3. Start with a broad search, then progressively narrow using additional constraints
   until you converge on a single dataset.
4. Copy the dataset identifier verbatim from the tool output. Do NOT fabricate identifiers.

RULES
- You MUST call at least one tool to validate the dataset.
- The data_identifier you return MUST be copied exactly from tool output.
- If you cannot narrow to a single dataset, return the closest match and explain in
  `reasoning`.
"""


class DatasetResult(BaseModel):
    """Output schema for the dataset discovery agent."""
    data_identifier: str = Field(..., description="The dataset identifier copied verbatim from tool output")
    data_identifier_type: str = Field(
        ...,
        description='One of: lidvid, lid, collection_lid, bundle_lid, pds3_dataset_id, pds3_product_id, opus_id, ode_id, unknown'
    )
    reasoning: str = Field(..., description="Brief explanation of how the dataset was found")


dataset_agent = Agent(
    name="PDS Dataset Discovery Agent",
    instructions=SYSTEM_PROMPT,
    model="gpt-5.2",
    tools=[mcp],
    output_type=DatasetResult,
    model_settings=ModelSettings(
        store=True,
        reasoning=Reasoning(
            effort="high",
            summary="auto"
        )
    )
)


async def run(query: str) -> dict:
    """Run the agent with a single query and return the result with tool call tracking."""
    with trace("PDS Dataset Discovery Agent"):
        result = await Runner.run(
            dataset_agent,
            input=[{
                "role": "user",
                "content": [{"type": "input_text", "text": query}]
            }],
            run_config=RunConfig(trace_metadata={
                "__trace_source__": "simple-dataset-agent",
            })
        )

        tool_calls = extract_tool_calls_with_outputs(result)
        token_usage = extract_token_usage(result)

        return {
            "query": query,
            "output": result.final_output.model_dump(),
            "tool_calls": tool_calls,
            "tool_call_count": len(tool_calls),
            "token_usage": token_usage,
        }


if __name__ == "__main__":
    import asyncio
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "Find calibrated MRO CRISM targeted observations of Mars from 2007"
    result = asyncio.run(run(query))
    print(json.dumps(result, indent=2, default=str))
