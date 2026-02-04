"""PDS Catalog get statistics tool."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool

from .catalog_index import CatalogIndex


class PDSCatalogGetStatsInput(InputSchema):
    """Input schema for PDS Catalog get statistics tool."""

    pass  # No input parameters needed


class PDSCatalogGetStatsOutput(OutputSchema):
    """Output schema for PDS Catalog get statistics tool."""

    status: str = Field(..., description="Status of the operation")
    total_datasets: int = Field(..., description="Total number of datasets in the catalog")
    by_node: dict[str, int] = Field(..., description="Dataset counts by PDS node")
    by_pds_version: dict[str, int] = Field(..., description="Dataset counts by PDS version")
    by_type: dict[str, int] = Field(..., description="Dataset counts by type (bundle, collection, volume)")
    missions_count: int = Field(..., description="Total number of unique missions")
    targets_count: int = Field(..., description="Total number of unique targets")


@mcp_tool
class PDSCatalogGetStatsTool(BaseTool[PDSCatalogGetStatsInput, PDSCatalogGetStatsOutput]):
    """Get catalog statistics.

    Returns overview statistics about the PDS catalog including total dataset counts,
    breakdowns by node, PDS version, dataset type, and counts of unique missions and targets.
    """

    input_schema = PDSCatalogGetStatsInput
    output_schema = PDSCatalogGetStatsOutput

    async def _arun(self, params: PDSCatalogGetStatsInput) -> PDSCatalogGetStatsOutput:
        """Execute PDS Catalog get statistics."""
        index = CatalogIndex.get_instance()

        stats = index.get_stats()

        return PDSCatalogGetStatsOutput(
            status="success",
            total_datasets=stats["total_datasets"],
            by_node=stats["by_node"],
            by_pds_version=stats["by_pds_version"],
            by_type=stats["by_type"],
            missions_count=stats["missions_count"],
            targets_count=stats["targets_count"],
        )
