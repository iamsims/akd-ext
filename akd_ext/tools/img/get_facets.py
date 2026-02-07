"""IMG Atlas get facets tool for discovering available field values."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.img.client import IMGAtlasClient


class IMGFacetValueItem(OutputSchema):
    """A single facet value with its count."""

    value: str = Field(..., description="The facet value")
    count: int = Field(..., description="Number of products with this value")


class IMGGetFacetsInput(InputSchema):
    """Input schema for IMG Atlas get facets tool."""

    facet_field: str = Field(
        ...,
        description=(
            "Field to get values for. Valid fields: 'TARGET' (planetary targets), "
            "'ATLAS_MISSION_NAME' (mission names), 'ATLAS_INSTRUMENT_NAME' (instruments), "
            "'ATLAS_SPACECRAFT_NAME' (spacecraft), 'PRODUCT_TYPE' (EDR/RDR), "
            "'FRAME_TYPE' (FULL/SUBFRAME), 'FILTER_NAME' (camera filters), 'pds_standard' (PDS3/PDS4)"
        ),
    )
    limit: int = Field(default=100, description="(Optional) Maximum number of values to return (default 100)")
    target: str | None = Field(default=None, description="(Optional) Target filter to narrow results (e.g., 'Mars')")
    mission: str | None = Field(default=None, description="(Optional) Mission filter to narrow results (e.g., 'MSL')")
    instrument: str | None = Field(
        default=None, description="(Optional) Instrument filter to narrow results (e.g., 'MASTCAM')"
    )


class IMGGetFacetsOutput(OutputSchema):
    """Output schema for IMG Atlas get facets tool."""

    status: str = Field(..., description="Status of the operation ('success' or 'error')")
    facet_field: str = Field(..., description="The field that was queried")
    query_time_ms: int = Field(..., description="Query execution time in milliseconds")
    count: int = Field(..., description="Number of values returned")
    values: list[IMGFacetValueItem] = Field(..., description="List of values with their counts, sorted by count descending")
    error: str | None = Field(default=None, description="Error message if status is 'error'")


@mcp_tool
class IMGGetFacetsTool(BaseTool[IMGGetFacetsInput, IMGGetFacetsOutput]):
    """Get available values and counts for a field in the IMG Atlas archive.

    Use this tool to dynamically discover available targets, missions, instruments,
    product types, and other field values. This is more accurate than static lists
    as it queries the actual archive data.

    Results are sorted by count in descending order, showing the most common values first.
    """

    input_schema = IMGGetFacetsInput
    output_schema = IMGGetFacetsOutput

    async def _arun(self, params: IMGGetFacetsInput) -> IMGGetFacetsOutput:
        """Execute IMG Atlas get facets."""
        async with IMGAtlasClient() as client:
            response = await client.get_facets(
                facet_field=params.facet_field,
                limit=params.limit,
                target=params.target,
                mission=params.mission,
                instrument=params.instrument,
            )

            if response.status == "error":
                return IMGGetFacetsOutput(
                    status="error",
                    facet_field=params.facet_field,
                    query_time_ms=0,
                    count=0,
                    values=[],
                    error=response.error,
                )

            return IMGGetFacetsOutput(
                status="success",
                facet_field=response.facet_field,
                query_time_ms=response.query_time_ms,
                count=len(response.values),
                values=[IMGFacetValueItem(value=v.value, count=v.count) for v in response.values],
            )
