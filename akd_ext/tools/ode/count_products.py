"""ODE count products tool for estimating data availability."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.ode.client import ODEClient


class ODECountProductsInput(InputSchema):
    """Input schema for ODE count products tool."""

    target: str = Field(..., description="Planetary body (mars, moon, mercury, phobos, deimos, venus)")
    ihid: str = Field(..., description='Instrument Host ID (e.g., "MRO", "LRO", "MESS")')
    iid: str = Field(..., description='Instrument ID (e.g., "HIRISE", "CTX", "LROC")')
    pt: str = Field(..., description='Product Type (e.g., "RDRV11", "EDR")')
    minlat: float | None = Field(default=None, description="(Optional) Minimum latitude (-90 to 90)")
    maxlat: float | None = Field(default=None, description="(Optional) Maximum latitude (-90 to 90)")
    westlon: float | None = Field(default=None, description="(Optional) Western longitude")
    eastlon: float | None = Field(default=None, description="(Optional) Eastern longitude")
    minobtime: str | None = Field(
        default=None, description='(Optional) Minimum observation time in UTC format (e.g., "2020-01-01")'
    )
    maxobtime: str | None = Field(
        default=None, description='(Optional) Maximum observation time in UTC format (e.g., "2020-01-31")'
    )


class ODECountProductsOutput(OutputSchema):
    """Output schema for ODE count products tool."""

    status: str = Field(..., description="Response status (SUCCESS or ERROR)")
    count: int = Field(..., description="Number of products matching the criteria")
    error: str | None = Field(default=None, description="Error message if status is ERROR")


@mcp_tool
class ODECountProductsTool(BaseTool[ODECountProductsInput, ODECountProductsOutput]):
    """Count products matching search criteria without retrieving full product details.

    This tool provides a fast way to estimate data availability for a given set of search parameters,
    including instrument, geographic bounds, and temporal range. Use this to gauge dataset size before
    running full product searches.

    Use this tool to check data availability and estimate result sizes before detailed searches.
    """

    input_schema = ODECountProductsInput
    output_schema = ODECountProductsOutput

    async def _arun(self, params: ODECountProductsInput) -> ODECountProductsOutput:
        """Execute ODE product count query."""
        async with ODEClient() as client:
            response = await client.count_products(
                target=params.target,
                ihid=params.ihid,
                iid=params.iid,
                pt=params.pt,
                minlat=params.minlat,
                maxlat=params.maxlat,
                westlon=params.westlon,
                eastlon=params.eastlon,
                minobtime=params.minobtime,
                maxobtime=params.maxobtime,
            )

            return ODECountProductsOutput(
                status=response.status,
                count=response.count,
                error=response.error,
            )
