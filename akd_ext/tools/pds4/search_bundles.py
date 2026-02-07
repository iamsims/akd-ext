"""PDS4 search bundles tool for discovering high-level data bundles."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import (
    PDS4HarvestInfo,
    PDS4IdentificationArea,
    PDS4InvestigationArea,
    PDS4SearchResponse,
    PDS4TargetIdentification,
    PDS4TimeCoordinates,
)


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


class PDS4BundleResult(OutputSchema):
    """Result model for a single bundle in search results."""

    id: str = Field(..., description="The bundle identifier")
    lid: str | None = Field(default=None, description="Logical identifier")
    lidvid: str | None = Field(default=None, description="Logical identifier with version")
    title: str | None = Field(default=None, description="Bundle title")
    investigation_area: PDS4InvestigationArea | None = Field(default=None, description="Investigation area details")
    identification_area: PDS4IdentificationArea | None = Field(default=None, description="Identification area details")
    target_identification: PDS4TargetIdentification | None = Field(default=None, description="Target identification details")
    time_coordinates: PDS4TimeCoordinates | None = Field(default=None, description="Time coordinates details")
    harvest_info: PDS4HarvestInfo | None = Field(default=None, description="Harvest information details")


class PDS4SearchBundlesOutput(OutputSchema):
    """Output schema for PDS4 search bundles tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    bundles: list[PDS4BundleResult] = Field(..., description="List of bundle results")
    facets: dict[str, dict[str, int]] = Field(..., description="Faceted search results")


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

            bundles = [
                PDS4BundleResult(
                    id=bundle.id,
                    lid=bundle.lid,
                    lidvid=bundle.lidvid,
                    title=bundle.title,
                    investigation_area=bundle.investigation_area,
                    identification_area=bundle.identification_area,
                    target_identification=bundle.target_identification,
                    time_coordinates=bundle.time_coordinates,
                    harvest_info=bundle.harvest_info,
                )
                for bundle in response.data
            ]

            facets = {facet.property: facet.counts for facet in response.facets}

            return PDS4SearchBundlesOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit or 0,
                bundles=bundles,
                facets=facets,
            )
