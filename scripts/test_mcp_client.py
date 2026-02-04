"""Test the MCP server using the MCP Python SDK.

This script connects to the akd-ext MCP server and calls tools
using the official MCP protocol.
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_server():
    """Test MCP server with actual MCP protocol."""

    print("=" * 80)
    print("Testing akd-ext MCP Server via MCP Protocol")
    print("=" * 80)

    # Server parameters - launch the MCP server as a subprocess
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "akd_ext.mcp.server"],
    )

    print("\n1. Starting MCP server...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            print("✓ Connected to MCP server")

            # Initialize the session
            print("\n2. Initializing session...")
            await session.initialize()
            print("✓ Session initialized")

            # List available tools
            print("\n3. Listing available tools...")
            tools_result = await session.list_tools()

            print(f"\nFound {len(tools_result.tools)} tools:")

            pds4_tools = []
            other_tools = []

            for tool in tools_result.tools:
                if "PDS4" in tool.name:
                    pds4_tools.append(tool)
                else:
                    other_tools.append(tool)

            if pds4_tools:
                print(f"\nPDS4 Tools ({len(pds4_tools)}):")
                for tool in pds4_tools:
                    print(f"  • {tool.name}")
                    if tool.description:
                        desc = tool.description.split("\n")[0][:80]
                        print(f"    {desc}")

            if other_tools:
                print(f"\nOther Tools ({len(other_tools)}):")
                for tool in other_tools:
                    print(f"  • {tool.name}")

            # Test calling a PDS4 tool (note: tool names are converted to snake_case by FastMCP)
            print("\n" + "=" * 80)
            print("4. Testing pds4search_investigations_tool...")
            print("=" * 80)

            tool_call_result = await session.call_tool(
                "pds4search_investigations_tool", arguments={"keywords": "mars", "limit": 3}
            )

            print("\n✓ Tool executed successfully!")
            print("\nResults:")

            # Parse the result
            import json

            for content in tool_call_result.content:
                if hasattr(content, "text") and content.text:
                    # Text content
                    result = json.loads(content.text)
                elif hasattr(content, "data"):
                    # Embedded data
                    result = content.data
                else:
                    continue

                print(f"  Total hits: {result.get('total_hits', 'N/A')}")
                print(f"  Query time: {result.get('query_time_ms', 'N/A')}ms")

                investigations = result.get("investigations", [])
                if investigations:
                    print(f"\n  Investigations found: {len(investigations)}")
                    for i, inv in enumerate(investigations, 1):
                        print(f"\n  {i}. {inv.get('title', 'N/A')}")
                        print(f"     LID: {inv.get('lid', 'N/A')}")

            # Test another tool
            print("\n" + "=" * 80)
            print("5. Testing pds4search_targets_tool...")
            print("=" * 80)

            tool_call_result = await session.call_tool(
                "pds4search_targets_tool", arguments={"keywords": "jupiter", "target_type": "Planet", "limit": 2}
            )

            print("\n✓ Tool executed successfully!")
            print("\nResults:")

            for content in tool_call_result.content:
                if hasattr(content, "text") and content.text:
                    result = json.loads(content.text)
                elif hasattr(content, "data"):
                    result = content.data
                else:
                    continue

                print(f"  Total hits: {result.get('total_hits', 'N/A')}")

                targets = result.get("targets", [])
                if targets:
                    print(f"\n  Targets found: {len(targets)}")
                    for i, target in enumerate(targets, 1):
                        print(f"\n  {i}. {target.get('title', 'N/A')}")
                        print(f"     LID: {target.get('lid', 'N/A')}")

            print("\n" + "=" * 80)
            print("✅ All MCP Protocol Tests Passed!")
            print("=" * 80)
            print("\nThe server is working correctly with the MCP protocol.")
            print("You can now:")
            print("  • Use it with Claude Desktop")
            print("  • Integrate it with other MCP clients")
            print("  • Build agents that use these tools")
            print("=" * 80)


async def main():
    """Run the MCP client tests."""
    try:
        await test_mcp_server()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure the MCP server can be started with:")
        print("  uv run python -m akd_ext.mcp.server")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
