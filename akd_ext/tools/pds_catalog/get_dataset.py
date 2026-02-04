"""PDS Catalog get dataset tool."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool

from .catalog_index import FULL_FIELDS, CatalogIndex, filter_dataset


class PDSCatalogGetDatasetInput(InputSchema):
    """Input schema for PDS Catalog get dataset tool."""

    dataset_id: str = Field(..., description="The dataset ID (LIDVID for PDS4, VOLUME_ID for PDS3)")


class PDSCatalogGetDatasetOutput(OutputSchema):
    """Output schema for PDS Catalog get dataset tool."""

    status: str = Field(..., description="Status of the operation ('success' or 'not_found')")
    dataset: dict | None = Field(default=None, description="Full dataset information if found")
    error: str | None = Field(default=None, description="Error message if dataset not found")


@mcp_tool
class PDSCatalogGetDatasetTool(BaseTool[PDSCatalogGetDatasetInput, PDSCatalogGetDatasetOutput]):
    """Get detailed information about a specific PDS dataset by ID.

    Retrieves complete metadata for a dataset including all fields such as
    description, missions, targets, instruments, temporal coverage, URLs, etc.
    """

    input_schema = PDSCatalogGetDatasetInput
    output_schema = PDSCatalogGetDatasetOutput

    async def _arun(self, params: PDSCatalogGetDatasetInput) -> PDSCatalogGetDatasetOutput:
        """Execute PDS Catalog get dataset."""
        index = CatalogIndex.get_instance()

        dataset = index.get_dataset(params.dataset_id)

        if dataset:
            return PDSCatalogGetDatasetOutput(
                status="success",
                dataset=filter_dataset(dataset, FULL_FIELDS),
            )

        return PDSCatalogGetDatasetOutput(
            status="not_found",
            error=f"Dataset not found: {params.dataset_id}",
        )
