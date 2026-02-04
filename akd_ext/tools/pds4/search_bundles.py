"""PDS4 search bundles tool for discovering high-level data bundles."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import PDS4SearchResponse


class PDS4SearchBundlesInput(InputSchema):
    """Input schema for PDS4 search bundles tool."""

    title_query: str | None = Field(
        default=None, description="(Optional) Search query for bundle titles (e.g., 'Lunar', 'Mars')"
    )
    start_time: str | None = Field(
        default=None, description="(Optional) Start of time range (ISO 8601 format, e.g., '2020-01-01T00:00:00Z')"
    )
    end_time: str | None = Field(default=None, description="(Optional) End of time range (ISO 8601 format)")
    processing_level: str | None = Field(
        default=None, description='(Optional) Filter by processing level ("Raw", "Calibrated", "Derived")'
    )
    limit: int = Field(
        default=0, description="(Optional, default: 0) Number of actual products to return (set to 0 for facets only)"
    )
    facet_fields: str | None = Field(
        default=None,
        description="(Optional) Comma-separated list of fields to facet on (e.g., 'pds:Identification_Area.pds:title,lidvid')",
    )
    facet_limit: int = Field(default=25, description="(Optional, default: 25) Maximum number of facet values to return")


class PDS4SearchBundlesOutput(OutputSchema):
    """Output schema for PDS4 search bundles tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    bundles: list[dict] = Field(..., description="List of bundle results")
    facets: dict = Field(..., description="Faceted search results")


@mcp_tool
class PDS4SearchBundlesTool(BaseTool[PDS4SearchBundlesInput, PDS4SearchBundlesOutput]):
    """Search for bundles in PDS4 with comprehensive results.

    Bundles are the highest-level organizational unit in PDS4, containing collections of related data.
    This tool supports faceted search for discovery workflows.

    Use for high-level data discovery and exploration via faceting.
    """

    input_schema = PDS4SearchBundlesInput
    output_schema = PDS4SearchBundlesOutput

    async def _arun(self, params: PDS4SearchBundlesInput) -> PDS4SearchBundlesOutput:
        """Execute PDS4 bundle search."""
        async with PDS4Client() as client:
            facet_field_list = None
            if params.facet_fields:
                facet_field_list = [field.strip() for field in params.facet_fields.split(",")]

            response: PDS4SearchResponse = await client.search_bundles(
                title_query=params.title_query,
                start_time=params.start_time,
                end_time=params.end_time,
                processing_level=params.processing_level,
                limit=params.limit,
                facet_fields=facet_field_list,
                facet_limit=params.facet_limit,
            )

            bundles = []
            for bundle in response.data:
                bundle_data = {
                    "id": bundle.id,
                    "lid": bundle.lid,
                    "lidvid": bundle.lidvid,
                    "title": bundle.title,
                }

                if bundle.investigation_area:
                    bundle_data["investigation_area"] = bundle.investigation_area.model_dump(exclude_none=True)
                if bundle.identification_area:
                    bundle_data["identification_area"] = bundle.identification_area.model_dump(exclude_none=True)
                if bundle.target_identification:
                    bundle_data["target_identification"] = bundle.target_identification.model_dump(exclude_none=True)
                if bundle.time_coordinates:
                    bundle_data["time_coordinates"] = bundle.time_coordinates.model_dump(exclude_none=True)
                if bundle.harvest_info:
                    bundle_data["harvest_info"] = bundle.harvest_info.model_dump(exclude_none=True)

                bundles.append(bundle_data)

            facets = {}
            for facet in response.facets:
                facets[facet.property] = facet.counts

            return PDS4SearchBundlesOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit or 0,
                bundles=bundles,
                facets=facets,
            )
