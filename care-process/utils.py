from agents import HostedMCPTool
from agents.items import ToolCallItem, ToolCallOutputItem
import os


def make_mcp_tool() -> HostedMCPTool:
    """Create the standard PDS MCP hosted tool with the full allowed_tools list."""
    return HostedMCPTool(tool_config={
        "type": "mcp",
        "server_label": "pds_mcp_server",
        "server_url": "https://complex-chocolate-python.fastmcp.app/mcp",
        "authorization": os.getenv("FAST_MCP_AUTH"),
        "allowed_tools": [
            "img_count_tool",
            "img_get_facets_tool",
            "img_get_product_tool",
            "img_search_tool",
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
            "sbn_list_sources_tool",
            "sbn_search_coordinates_tool",
            "sbn_search_object_tool",
        ],
        "require_approval": "never",
    })


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
