"""IMG Atlas count products tool for counting imagery products without retrieval."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.img.client import IMGAtlasClient


class IMGAppliedFilters(OutputSchema):
    """Filters that were applied to a count or search query."""

    target: str | None = Field(default=None, description="Target body filter")
    mission: str | None = Field(default=None, description="Mission name filter")
    instrument: str | None = Field(default=None, description="Instrument name filter")
    spacecraft: str | None = Field(default=None, description="Spacecraft name filter")
    start_time: str | None = Field(default=None, description="Start time filter (ISO 8601)")
    stop_time: str | None = Field(default=None, description="Stop time filter (ISO 8601)")
    sol_min: int | None = Field(default=None, description="Minimum sol number for Mars missions")
    sol_max: int | None = Field(default=None, description="Maximum sol number for Mars missions")
    product_type: str | None = Field(default=None, description="Product type filter (EDR, RDR)")
    filter_name: str | None = Field(default=None, description="Camera filter name filter")
    frame_type: str | None = Field(default=None, description="Frame type filter")
    exposure_min: float | None = Field(default=None, description="Minimum exposure duration in milliseconds")
    exposure_max: float | None = Field(default=None, description="Maximum exposure duration in milliseconds")
    local_solar_time: str | None = Field(default=None, description="Local true solar time filter")


class IMGCountProductsInput(InputSchema):
    """Input schema for IMG Atlas count products tool."""

    target: str | None = Field(default=None, description="(Optional) Target body filter (e.g., 'Mars', 'Saturn')")
    mission: str | None = Field(
        default=None, description="(Optional) Mission name filter (e.g., 'MARS SCIENCE LABORATORY')"
    )
    instrument: str | None = Field(default=None, description="(Optional) Instrument name filter (e.g., 'MASTCAM')")
    spacecraft: str | None = Field(default=None, description="(Optional) Spacecraft name filter (e.g., 'CURIOSITY')")
    start_time: str | None = Field(default=None, description="(Optional) Start of time range (ISO 8601 format)")
    stop_time: str | None = Field(default=None, description="(Optional) End of time range (ISO 8601 format)")
    sol_min: int | None = Field(default=None, description="(Optional) Minimum sol number for Mars missions")
    sol_max: int | None = Field(default=None, description="(Optional) Maximum sol number for Mars missions")
    product_type: str | None = Field(default=None, description="(Optional) Product type filter ('EDR', 'RDR')")
    filter_name: str | None = Field(default=None, description="(Optional) Camera filter name (e.g., 'L0', 'R0', 'RED')")
    frame_type: str | None = Field(default=None, description="(Optional) Frame type filter (e.g., 'FULL', 'SUBFRAME')")
    exposure_min: float | None = Field(default=None, description="(Optional) Minimum exposure duration in milliseconds")
    exposure_max: float | None = Field(default=None, description="(Optional) Maximum exposure duration in milliseconds")
    local_solar_time: str | None = Field(
        default=None, description="(Optional) Local true solar time filter (e.g., '12:00')"
    )


class IMGCountProductsOutput(OutputSchema):
    """Output schema for IMG Atlas count products tool."""

    status: str = Field(..., description="Status of the count operation ('success' or 'error')")
    count: int = Field(..., description="Number of products matching the criteria")
    query_time_ms: int = Field(..., description="Query execution time in milliseconds")
    filters: IMGAppliedFilters = Field(..., description="Applied filters for reference")
    error: str | None = Field(default=None, description="Error message if status is 'error'")


@mcp_tool
class IMGCountProductsTool(BaseTool[IMGCountProductsInput, IMGCountProductsOutput]):
    """Count imagery products matching criteria without retrieving them.

    Useful for understanding data availability before running full searches.
    This is much faster than searching when you only need to know how many products exist.
    """

    input_schema = IMGCountProductsInput
    output_schema = IMGCountProductsOutput

    async def _arun(self, params: IMGCountProductsInput) -> IMGCountProductsOutput:
        """Execute IMG Atlas product count."""
        async with IMGAtlasClient() as client:
            response = await client.count_products(
                target=params.target,
                mission=params.mission,
                instrument=params.instrument,
                spacecraft=params.spacecraft,
                start_time=params.start_time,
                stop_time=params.stop_time,
                sol_min=params.sol_min,
                sol_max=params.sol_max,
                product_type=params.product_type,
                filter_name=params.filter_name,
                frame_type=params.frame_type,
                exposure_min=params.exposure_min,
                exposure_max=params.exposure_max,
                local_solar_time=params.local_solar_time,
            )

            if response.status == "error":
                return IMGCountProductsOutput(
                    status="error",
                    count=0,
                    query_time_ms=0,
                    filters=IMGAppliedFilters(),
                    error=response.error,
                )

            return IMGCountProductsOutput(
                status="success",
                count=response.count,
                query_time_ms=response.query_time_ms,
                filters=IMGAppliedFilters(
                    target=params.target,
                    mission=params.mission,
                    instrument=params.instrument,
                    spacecraft=params.spacecraft,
                    start_time=params.start_time,
                    stop_time=params.stop_time,
                    sol_min=params.sol_min,
                    sol_max=params.sol_max,
                    product_type=params.product_type,
                    filter_name=params.filter_name,
                    frame_type=params.frame_type,
                    exposure_min=params.exposure_min,
                    exposure_max=params.exposure_max,
                    local_solar_time=params.local_solar_time,
                ),
            )
