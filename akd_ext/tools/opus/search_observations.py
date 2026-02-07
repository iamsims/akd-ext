"""OPUS search observations tool for discovering outer planets observations."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.opus.client import OPUSClient


class OPUSObservationResult(OutputSchema):
    """OPUS observation result from search."""

    opusid: str = Field(..., description="OPUS observation identifier")
    instrument: str = Field(..., description="Instrument name")
    planet: str = Field(..., description="Target planet")
    target: str = Field(..., description="Observation target")
    mission: str = Field(..., description="Space mission name")
    time1: str = Field(..., description="Observation start time")
    time2: str = Field(..., description="Observation end time")
    observation_duration: float = Field(..., description="Observation duration in seconds")
    ring_obs_id: str = Field(..., description="Ring observation identifier")


class OPUSSearchObservationsInput(InputSchema):
    """Input schema for OPUS search observations tool."""

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
    limit: int = Field(default=100, description="(Optional, default: 100) Maximum observations to return")
    startobs: int = Field(default=1, description="(Optional, default: 1) Starting observation index for pagination")
    order: str = Field(
        default="time1,opusid", description="(Optional, default: 'time1,opusid') Sort order (e.g., 'time1,opusid')"
    )


class OPUSSearchObservationsOutput(OutputSchema):
    """Output schema for OPUS search observations tool."""

    status: str = Field(..., description="Response status (success or error)")
    start_obs: int = Field(..., description="Starting observation index")
    limit: int = Field(..., description="Maximum results requested")
    count: int = Field(..., description="Number of observations returned")
    available: int = Field(..., description="Total available observations matching criteria")
    order: str = Field(..., description="Sort order used")
    observations: list[OPUSObservationResult] = Field(..., description="List of observation results")
    error: str | None = Field(default=None, description="Error message if status is error")


@mcp_tool
class OPUSSearchObservationsTool(BaseTool[OPUSSearchObservationsInput, OPUSSearchObservationsOutput]):
    """Search for observations in OPUS (Outer Planets Unified Search).

    OPUS provides access to 400,000+ observations from outer planets missions including
    Cassini, Voyager 1/2, Galileo, New Horizons, Juno, and Hubble Space Telescope.

    Supports filtering by target, mission, instrument, planet, and time range with pagination.
    """

    input_schema = OPUSSearchObservationsInput
    output_schema = OPUSSearchObservationsOutput

    async def _arun(self, params: OPUSSearchObservationsInput) -> OPUSSearchObservationsOutput:
        """Execute OPUS observation search."""
        async with OPUSClient() as client:
            response = await client.search_observations(
                target=params.target,
                mission=params.mission,
                instrument=params.instrument,
                planet=params.planet,
                time_min=params.time_min,
                time_max=params.time_max,
                limit=params.limit,
                startobs=params.startobs,
                order=params.order,
            )

            observations = []
            for obs in response.observations:
                observations.append(
                    OPUSObservationResult(
                        opusid=obs.opusid,
                        instrument=obs.instrument or "",
                        planet=obs.planet or "",
                        target=obs.target or "",
                        mission=obs.mission or "",
                        time1=obs.time1 or "",
                        time2=obs.time2 or "",
                        observation_duration=obs.observation_duration or 0.0,
                        ring_obs_id=obs.ring_obs_id or "",
                    )
                )

            return OPUSSearchObservationsOutput(
                status=response.status,
                start_obs=response.start_obs,
                limit=response.limit,
                count=response.count,
                available=response.available,
                order=response.order,
                observations=observations,
                error=response.error,
            )
