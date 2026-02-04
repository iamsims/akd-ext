"""SBN CATCH search fixed target tool."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool

from .client import SBNCatchClient
from .models import CatchObservation


class SBNSearchFixedTargetInput(InputSchema):
    """Input schema for SBN CATCH search fixed target tool."""

    ra: str = Field(
        ...,
        description="Right ascension (sexagesimal HH:MM:SS or decimal degrees)",
    )
    dec: str = Field(
        ...,
        description="Declination (sexagesimal ±DD:MM:SS or decimal degrees)",
    )
    sources: list[str] | None = Field(
        default=None,
        description="(Optional) List of data sources to search (None = all sources)",
    )
    radius: float = Field(
        default=10.0,
        description="(Optional, default: 10.0) Search radius in arcminutes (0-120)",
    )
    start_date: str | None = Field(
        default=None,
        description="(Optional) Start date filter (format: 'YYYY-MM-DD HH:MM')",
    )
    stop_date: str | None = Field(
        default=None,
        description="(Optional) Stop date filter (format: 'YYYY-MM-DD HH:MM')",
    )
    intersection_type: str | None = Field(
        default=None,
        description="(Optional) How search area intersects images (ImageIntersectsArea, ImageContainsArea, AreaContainsImage)",
    )


class SBNSearchFixedTargetOutput(OutputSchema):
    """Output schema for SBN CATCH search fixed target tool."""

    status: str = Field(..., description="Status of the operation (success or error)")
    count: int = Field(..., description="Number of observations found")
    observations: list[CatchObservation] = Field(..., description="List of observations")
    error: str | None = Field(None, description="Error message if operation failed")


@mcp_tool
class SBNSearchFixedTargetTool(BaseTool[SBNSearchFixedTargetInput, SBNSearchFixedTargetOutput]):
    """Search for observations at fixed sky coordinates in the SBN CATCH API.

    This tool searches for observations at a specific RA/Dec position across multiple
    astronomical surveys. Useful for finding serendipitous observations of objects
    at known positions or for general area searches.
    """

    input_schema = SBNSearchFixedTargetInput
    output_schema = SBNSearchFixedTargetOutput

    async def _arun(self, params: SBNSearchFixedTargetInput) -> SBNSearchFixedTargetOutput:
        """Execute SBN CATCH search fixed target."""
        async with SBNCatchClient() as client:
            response = await client.search_fixed_target(
                ra=params.ra,
                dec=params.dec,
                sources=params.sources,
                radius=params.radius,
                start_date=params.start_date,
                stop_date=params.stop_date,
                intersection_type=params.intersection_type,
            )

        return SBNSearchFixedTargetOutput(
            status=response.status,
            count=response.count,
            observations=response.observations,
            error=response.error,
        )
