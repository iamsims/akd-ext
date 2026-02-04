"""OPUS count observations tool for getting observation counts without retrieving data."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.opus.client import OPUSClient


class OPUSCountObservationsInput(InputSchema):
    """Input schema for OPUS count observations tool."""

    target: str | None = Field(
        default=None, description="(Optional) Target body (e.g., 'Saturn', 'Titan', 'Saturn Rings')"
    )
    mission: str | None = Field(
        default=None,
        description="(Optional) Mission name (e.g., 'Cassini', 'Voyager', 'Galileo', 'New Horizons', 'Juno', 'HST')",
    )
    instrument: str | None = Field(
        default=None, description="(Optional) Instrument name (e.g., 'Cassini ISS', 'Voyager ISS', 'LORRI')"
    )
    planet: str | None = Field(
        default=None, description="(Optional) Planet filter (jupiter, saturn, uranus, neptune, pluto, other)"
    )
    time_min: str | None = Field(default=None, description="(Optional) Start of time range (ISO 8601 format)")
    time_max: str | None = Field(default=None, description="(Optional) End of time range (ISO 8601 format)")


class OPUSCountObservationsOutput(OutputSchema):
    """Output schema for OPUS count observations tool."""

    status: str = Field(..., description="Response status (success or error)")
    count: int = Field(..., description="Number of observations matching criteria")
    error: str | None = Field(default=None, description="Error message if status is error")


@mcp_tool
class OPUSCountObservationsTool(BaseTool[OPUSCountObservationsInput, OPUSCountObservationsOutput]):
    """Count observations matching criteria without retrieving them.

    Efficiently get the count of observations matching search criteria without
    downloading the full observation data. Useful for determining result set size
    before pagination.
    """

    input_schema = OPUSCountObservationsInput
    output_schema = OPUSCountObservationsOutput

    async def _arun(self, params: OPUSCountObservationsInput) -> OPUSCountObservationsOutput:
        """Execute OPUS observation count."""
        async with OPUSClient() as client:
            response = await client.count_observations(
                target=params.target,
                mission=params.mission,
                instrument=params.instrument,
                planet=params.planet,
                time_min=params.time_min,
                time_max=params.time_max,
            )

            return OPUSCountObservationsOutput(
                status=response.status,
                count=response.count,
                error=response.error,
            )
