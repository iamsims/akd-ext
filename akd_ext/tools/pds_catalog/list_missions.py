"""PDS Catalog list missions tool."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool

from .catalog_index import CatalogIndex


class PDSCatalogListMissionsInput(InputSchema):
    """Input schema for PDS Catalog list missions tool."""

    node: str | None = Field(default=None, description="(Optional) Filter by PDS node")
    limit: int = Field(default=50, description="(Optional, default: 50) Maximum missions to return")


class PDSCatalogListMissionsOutput(OutputSchema):
    """Output schema for PDS Catalog list missions tool."""

    status: str = Field(..., description="Status of the operation")
    count: int = Field(..., description="Number of missions returned")
    missions: list[dict] = Field(..., description="List of missions with dataset counts")


@mcp_tool
class PDSCatalogListMissionsTool(BaseTool[PDSCatalogListMissionsInput, PDSCatalogListMissionsOutput]):
    """List missions available in the PDS catalog.

    Returns a list of mission names with the count of datasets for each mission
    and which PDS nodes have data for that mission.
    """

    input_schema = PDSCatalogListMissionsInput
    output_schema = PDSCatalogListMissionsOutput

    async def _arun(self, params: PDSCatalogListMissionsInput) -> PDSCatalogListMissionsOutput:
        """Execute PDS Catalog list missions."""
        index = CatalogIndex.get_instance()

        missions = index.list_missions()

        if params.node:
            missions = [m for m in missions if params.node.lower() in m["nodes"]]

        missions = missions[: params.limit]

        return PDSCatalogListMissionsOutput(
            status="success",
            count=len(missions),
            missions=missions,
        )
