"""PDS Catalog list targets tool."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool

from .catalog_index import CatalogIndex


class PDSCatalogListTargetsInput(InputSchema):
    """Input schema for PDS Catalog list targets tool."""

    node: str | None = Field(default=None, description="(Optional) Filter by PDS node")
    limit: int = Field(default=50, description="(Optional, default: 50) Maximum targets to return")


class PDSCatalogListTargetsOutput(OutputSchema):
    """Output schema for PDS Catalog list targets tool."""

    status: str = Field(..., description="Status of the operation")
    count: int = Field(..., description="Number of targets returned")
    targets: list[dict] = Field(..., description="List of targets with dataset counts")


@mcp_tool
class PDSCatalogListTargetsTool(BaseTool[PDSCatalogListTargetsInput, PDSCatalogListTargetsOutput]):
    """List celestial body targets available in the PDS catalog.

    Returns a list of target bodies (planets, moons, asteroids, comets, etc.)
    with the count of datasets for each target and which PDS nodes have data
    for that target.
    """

    input_schema = PDSCatalogListTargetsInput
    output_schema = PDSCatalogListTargetsOutput

    async def _arun(self, params: PDSCatalogListTargetsInput) -> PDSCatalogListTargetsOutput:
        """Execute PDS Catalog list targets."""
        index = CatalogIndex.get_instance()

        targets = index.list_targets()

        if params.node:
            targets = [t for t in targets if params.node.lower() in t["nodes"]]

        targets = targets[: params.limit]

        return PDSCatalogListTargetsOutput(
            status="success",
            count=len(targets),
            targets=targets,
        )
