"""Test PDS4 tools are registered with MCP server."""

from akd_ext.mcp.server import mcp
from akd_ext.mcp.registry import MCPToolRegistry


def test_tools_registered():
    """Check which tools are registered with the MCP server."""

    print("=" * 80)
    print("Checking MCP Tool Registration")
    print("=" * 80)

    # Get all registered tools from the registry
    registry = MCPToolRegistry()
    tool_classes = registry.get_tools()

    print(f"\nTotal tools registered: {len(tool_classes)}")
    print("\nRegistered tools:")

    pds4_tools = []
    other_tools = []

    for tool_class in tool_classes:
        tool_name = tool_class.__name__
        if 'PDS4' in tool_name:
            pds4_tools.append(tool_name)
        else:
            other_tools.append(tool_name)

    if pds4_tools:
        print(f"\nPDS4 Tools ({len(pds4_tools)}):")
        for tool in sorted(pds4_tools):
            print(f"  ✓ {tool}")

    if other_tools:
        print(f"\nOther Tools ({len(other_tools)}):")
        for tool in sorted(other_tools):
            print(f"  ✓ {tool}")

    # Check FastMCP server tools
    print("\n" + "=" * 80)
    print("FastMCP Server Information")
    print("=" * 80)
    print(f"\nServer name: {mcp.name}")

    # Try to get tools from FastMCP (API may vary)
    try:
        # FastMCP stores tools internally
        if hasattr(mcp, '_tools'):
            print(f"FastMCP tools count: {len(mcp._tools)}")
        elif hasattr(mcp, 'tools'):
            print(f"FastMCP tools count: {len(mcp.tools)}")
    except Exception as e:
        print(f"Could not access FastMCP tools: {e}")


if __name__ == "__main__":
    test_tools_registered()
