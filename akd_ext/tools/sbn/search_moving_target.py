"""SBN CATCH search moving target tool."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool

from .client import SBNCatchClient
from .models import CatchObservation, CatchSourceStatus


class SBNSearchMovingTargetInput(InputSchema):
    """Input schema for SBN CATCH search moving target tool."""

    target: str = Field(
        ...,
        description="JPL Horizons-resolvable designation (e.g., '65803', '1P/Halley', '2019 DQ123')",
    )
    sources: list[str] | None = Field(
        default=None,
        description="List of data sources to search (None = all sources)",
    )
    start_date: str | None = Field(
        default=None,
        description="Start date filter (format: 'YYYY-MM-DD HH:MM')",
    )
    stop_date: str | None = Field(
        default=None,
        description="Stop date filter (format: 'YYYY-MM-DD HH:MM')",
    )
    uncertainty_ellipse: bool = Field(
        default=False,
        description="Include ephemeris uncertainty in search",
    )
    padding: float = Field(
        default=0.0,
        description="Search margin in arcminutes (0-120)",
    )
    cached: bool = Field(
        default=True,
        description="Use cached results if available",
    )
    timeout: float = Field(
        default=120.0,
        description="Maximum time to wait for job completion in seconds",
    )
    poll_interval: float = Field(
        default=2.0,
        description="Time between status checks in seconds",
    )


class SBNSearchMovingTargetOutput(OutputSchema):
    """Output schema for SBN CATCH search moving target tool."""

    status: str = Field(..., description="Status of the operation (success or error)")
    job_id: str = Field(..., description="Job ID for the search")
    count: int = Field(..., description="Number of observations found")
    observations: list[CatchObservation] = Field(..., description="List of observations")
    source_status: list[CatchSourceStatus] = Field(..., description="Status of each data source searched")
    error: str | None = Field(None, description="Error message if operation failed")


@mcp_tool
class SBNSearchMovingTargetTool(BaseTool[SBNSearchMovingTargetInput, SBNSearchMovingTargetOutput]):
    """Search for observations of a moving target (comet or asteroid) in the SBN CATCH API.

    This tool searches for observations of comets and asteroids across multiple astronomical
    surveys. It uses JPL Horizons for target ephemerides and returns observations with
    cutout URLs, preview images, and metadata.
    """

    input_schema = SBNSearchMovingTargetInput
    output_schema = SBNSearchMovingTargetOutput

    async def _arun(self, params: SBNSearchMovingTargetInput) -> SBNSearchMovingTargetOutput:
        """Execute SBN CATCH search moving target."""
        async with SBNCatchClient() as client:
            response = await client.search_and_wait(
                target=params.target,
                sources=params.sources,
                start_date=params.start_date,
                stop_date=params.stop_date,
                uncertainty_ellipse=params.uncertainty_ellipse,
                padding=params.padding,
                cached=params.cached,
                timeout=params.timeout,
                poll_interval=params.poll_interval,
            )

        return SBNSearchMovingTargetOutput(
            status=response.status,
            job_id=response.job_id,
            count=response.count,
            observations=response.observations,
            source_status=response.source_status,
            error=response.error,
        )
