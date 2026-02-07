"""PDS Catalog search datasets tool."""

from datetime import date

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool

from .catalog_index import (
    DEFAULT_RESULTS_LIMIT,
    FIELD_PROFILES,
    MAX_RESULTS_LIMIT,
    SUMMARY_FIELDS,
    CatalogIndex,
    filter_dataset,
)
from .models import PDSCatalogDatasetResult


class PDSCatalogSearchInput(InputSchema):
    """Input schema for PDS Catalog search tool."""

    query: str | None = Field(
        default=None,
        description="(Optional) Text search across title, description, missions, targets, instruments. "
        "Examples: 'mars images', 'cassini saturn', 'comet spectra'",
    )
    node: str | None = Field(
        default=None,
        description="(Optional) Filter by PDS node. Valid values: atm (Atmospheres), geo (Geosciences), "
        "img (Imaging), naif (SPICE/Navigation), ppi (Plasma), rms (Ring-Moon), sbn (Small Bodies)",
    )
    mission: str | None = Field(
        default=None, description="(Optional) Filter by mission name. Examples: 'Cassini', 'Mars 2020', 'Voyager'"
    )
    instrument: str | None = Field(
        default=None, description="(Optional) Filter by instrument name. Examples: 'JEDI', 'CAPS', 'magnetometer'"
    )
    target: str | None = Field(
        default=None, description="(Optional) Filter by target body. Examples: 'Mars', 'Saturn', 'Comet'"
    )
    pds_version: str | None = Field(default=None, description="(Optional) Filter by archive version: 'PDS3' or 'PDS4'")
    dataset_type: str | None = Field(
        default=None, description="(Optional) Filter by type: 'volume' (PDS3), 'bundle' (PDS4), or 'collection' (PDS4)"
    )
    start_date: str | None = Field(
        default=None, description="(Optional) Filter datasets that have data on or after this date (YYYY-MM-DD)"
    )
    stop_date: str | None = Field(
        default=None, description="(Optional) Filter datasets that have data on or before this date (YYYY-MM-DD)"
    )
    limit: int = Field(
        default=DEFAULT_RESULTS_LIMIT,
        description=f"(Optional, default: {DEFAULT_RESULTS_LIMIT}) Maximum results to return (max {MAX_RESULTS_LIMIT})",
    )
    offset: int = Field(default=0, description="(Optional, default: 0) Skip first N results for pagination")
    fields: str = Field(
        default="summary",
        description="(Optional, default: 'summary') Response detail level - 'essential', 'summary', or 'full'",
    )


class PDSCatalogSearchOutput(OutputSchema):
    """Output schema for PDS Catalog search tool."""

    status: str = Field(..., description="Status of the search operation")
    count: int = Field(..., description="Number of results returned")
    total: int = Field(..., description="Total number of matching datasets")
    offset: int = Field(..., description="Offset used for pagination")
    limit: int = Field(..., description="Limit used for results")
    has_more: bool = Field(..., description="Whether more results are available")
    fields: str = Field(..., description="Field profile used")
    datasets: list[PDSCatalogDatasetResult] = Field(..., description="List of matching datasets")


@mcp_tool
class PDSCatalogSearchTool(BaseTool[PDSCatalogSearchInput, PDSCatalogSearchOutput]):
    """Search the PDS dataset catalog across all 7 PDS nodes.

    This tool searches a pre-scraped catalog of PDS datasets, supporting text search,
    filtering by node/mission/target, temporal filtering, and pagination.
    Uses fuzzy matching for text queries to handle typos and variations.
    """

    input_schema = PDSCatalogSearchInput
    output_schema = PDSCatalogSearchOutput

    async def _arun(self, params: PDSCatalogSearchInput) -> PDSCatalogSearchOutput:
        """Execute PDS Catalog search."""
        index = CatalogIndex.get_instance()

        effective_limit = min(params.limit, MAX_RESULTS_LIMIT)
        field_set = FIELD_PROFILES.get(params.fields, SUMMARY_FIELDS)

        # Parse date strings to date objects
        parsed_start = date.fromisoformat(params.start_date) if params.start_date else None
        parsed_stop = date.fromisoformat(params.stop_date) if params.stop_date else None

        datasets, total = index.search(
            query=params.query,
            node=params.node,
            mission=params.mission,
            instrument=params.instrument,
            target=params.target,
            pds_version=params.pds_version,
            dataset_type=params.dataset_type,
            start_date=parsed_start,
            stop_date=parsed_stop,
            limit=effective_limit,
            offset=params.offset,
        )

        results = [PDSCatalogDatasetResult(**filter_dataset(d, field_set)) for d in datasets]
        has_more = params.offset + len(results) < total

        return PDSCatalogSearchOutput(
            status="success",
            count=len(results),
            total=total,
            offset=params.offset,
            limit=effective_limit,
            has_more=has_more,
            fields=params.fields,
            datasets=results,
        )
