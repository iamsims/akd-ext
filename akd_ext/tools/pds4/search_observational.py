"""PDS4 search observational products tool for finding observational data products."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import (
    PDS4DataFileInfo,
    PDS4IdentificationArea,
    PDS4PrimaryResultSummary,
    PDS4ScienceFacets,
    PDS4SearchResponse,
    PDS4TimeCoordinates,
)


class PDS4SearchObservationalInput(InputSchema):
    """Input schema for PDS4 search observational tool."""

    title_query: str | None = Field(
        default=None, description="(Optional) Search query for product titles (e.g., 'LRO', 'Mars')"
    )
    limit: int = Field(
        default=10, description="(Optional, default: 10) Number of actual products to return (set to 0 for facets only)"
    )
    facet_fields: str | None = Field(
        default=None,
        description="(Optional) Comma-separated list of fields to facet on (e.g., 'pds:Identification_Area.pds:title,lidvid')",
    )
    facet_limit: int = Field(default=25, description="(Optional, default: 25) Maximum number of facet values to return")


class PDS4ObservationalResult(OutputSchema):
    """Result model for a single observational product in search results."""

    id: str = Field(..., description="The product identifier")
    lid: str | None = Field(default=None, description="Logical identifier")
    lidvid: str | None = Field(default=None, description="Logical identifier with version")
    title: str | None = Field(default=None, description="Product title")
    identification_area: PDS4IdentificationArea | None = Field(default=None, description="Identification area details")
    science_facets: PDS4ScienceFacets | None = Field(default=None, description="Science facets details")
    time_coordinates: PDS4TimeCoordinates | None = Field(default=None, description="Time coordinates details")
    primary_result_summary: PDS4PrimaryResultSummary | None = Field(default=None, description="Primary result summary details")
    data_file_info: PDS4DataFileInfo | None = Field(default=None, description="Data file information")


class PDS4SearchObservationalOutput(OutputSchema):
    """Output schema for PDS4 search observational tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    products: list[PDS4ObservationalResult] = Field(..., description="List of observational product results")
    facets: dict[str, dict[str, int]] = Field(..., description="Faceted search results")


@mcp_tool
class PDS4SearchObservationalTool(BaseTool[PDS4SearchObservationalInput, PDS4SearchObservationalOutput]):
    """Search for observational products in PDS4.

    Observational products contain actual scientific observation data (images, spectra, etc.).
    This tool supports faceted search for discovery workflows.

    Use for direct search of observational data products.
    """

    input_schema = PDS4SearchObservationalInput
    output_schema = PDS4SearchObservationalOutput

    async def _arun(self, params: PDS4SearchObservationalInput) -> PDS4SearchObservationalOutput:
        """Execute PDS4 observational search."""
        async with PDS4Client() as client:
            facet_field_list = None
            if params.facet_fields:
                facet_field_list = [field.strip() for field in params.facet_fields.split(",")]

            response: PDS4SearchResponse = await client.search_observational(
                title_query=params.title_query,
                limit=params.limit,
                facet_fields=facet_field_list,
                facet_limit=params.facet_limit,
            )

            products = [
                PDS4ObservationalResult(
                    id=product.id,
                    lid=product.lid,
                    lidvid=product.lidvid,
                    title=product.title,
                    identification_area=product.identification_area,
                    science_facets=product.science_facets,
                    time_coordinates=product.time_coordinates,
                    primary_result_summary=product.primary_result_summary,
                    data_file_info=product.data_file_info,
                )
                for product in response.data
            ]

            facets = {facet.property: facet.counts for facet in response.facets}

            return PDS4SearchObservationalOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit,
                products=products,
                facets=facets,
            )
