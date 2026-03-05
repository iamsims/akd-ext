from agents import Agent, ModelSettings, Runner, RunConfig, WebSearchTool, trace, set_default_openai_client
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from openai.types.shared.reasoning import Reasoning
from dataclasses import dataclass, field
from utils import make_mcp_tool, extract_tool_calls_with_outputs, extract_token_usage
import dotenv
import os
import json

dotenv.load_dotenv()


# ---------------------------------------------------------------------------
# Default output schema (used when caller doesn't provide one)
# ---------------------------------------------------------------------------

class DatasetResult(BaseModel):
    """A single dataset match."""
    data_identifier: str = Field(..., description="The dataset identifier copied verbatim from tool output")
    data_identifier_type: str = Field(
        ...,
        description='One of: lidvid, lid, collection_lid, bundle_lid, pds3_dataset_id, pds3_product_id, opus_id, ode_id, unknown'
    )
    reasoning: str = Field(..., description="Brief explanation of how this dataset was found")


class DatasetResults(BaseModel):
    """Output schema for the dataset discovery agent — returns all matching datasets."""
    results: list[DatasetResult] = Field(..., description="List of matching datasets, ordered by relevance")


# ---------------------------------------------------------------------------
# Default system prompt (used for standalone / quick testing)
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """You are a Planetary Data System (PDS) dataset discovery agent.

Given a natural-language query from a user, use the available MCP tools to find the
matching PDS datasets and return their identifiers.

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
3. Start with a broad search, then progressively narrow using additional constraints.
4. Copy dataset identifiers verbatim from tool output. Do NOT fabricate identifiers.

RULES
- You MUST call at least one tool to validate datasets.
- Every data_identifier you return MUST be copied exactly from tool output.
- Return ALL relevant matching datasets, ordered by relevance.
- Provide reasoning for each individual dataset explaining why it matches.
"""


# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    """Configuration for the PDS agent. Pass a custom prompt / output_type / tools flag."""
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    use_mcp_tools: bool = True
    use_web_search: bool = False
    output_type: type[BaseModel] | None = None   # None → uses DatasetResults
    model: str = "gpt-5.2"
    reasoning_effort: str = "high"
    timeout: float = 1800.0


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def build_agent(config: AgentConfig) -> Agent:
    """Build an Agent instance from the given config."""
    tools = [make_mcp_tool()] if config.use_mcp_tools else []
    if config.use_web_search:
        tools.append(WebSearchTool(search_context_size="medium"))
    output_type = config.output_type or DatasetResults

    return Agent(
        name="PDS Dataset Discovery Agent",
        instructions=config.system_prompt,
        model=config.model,
        tools=tools,
        output_type=output_type,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(
                effort=config.reasoning_effort,
                summary="auto"
            )
        )
    )


def _setup_client(timeout: float):
    """Configure the global OpenAI client with the given timeout."""
    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=timeout
    )
    set_default_openai_client(client)


# ---------------------------------------------------------------------------
# Public run interface
# ---------------------------------------------------------------------------

async def run(query: str, config: AgentConfig | None = None) -> dict:
    """Run the agent with a single query and return the result with tool call tracking."""
    if config is None:
        config = AgentConfig()

    _setup_client(config.timeout)
    agent = build_agent(config)

    with trace("PDS Dataset Discovery Agent"):
        result = await Runner.run(
            agent,
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


# ---------------------------------------------------------------------------
# CLI entry point for quick standalone testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="PDS Dataset Discovery Agent")
    parser.add_argument("query", nargs="?",
                        default="Find calibrated MRO CRISM targeted observations of Mars from 2007")
    parser.add_argument("--no-tools", action="store_true",
                        help="Run without MCP tools")
    parser.add_argument("--web-search", action="store_true", default=False,
                        help="Enable web search tool (default: disabled)")
    parser.add_argument("--model", default="gpt-5.2")
    parser.add_argument("--reasoning-effort", default="high",
                        choices=["low", "medium", "high"])
    args = parser.parse_args()

    config = AgentConfig(
        use_mcp_tools=not args.no_tools,
        use_web_search=args.web_search,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    result = asyncio.run(run(args.query, config))
    print(json.dumps(result, indent=2, default=str))
