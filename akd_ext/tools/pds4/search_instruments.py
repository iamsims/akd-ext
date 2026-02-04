"""PDS4 search instruments tool for finding scientific instruments."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import PDS4SearchResponse


class PDS4SearchInstrumentsInput(InputSchema):
    """Input schema for PDS4 search instruments tool."""

    keywords: str | None = Field(
        default=None,
        description="(Optional) Search terms for instruments (e.g., 'camera mars', 'spectrometer cassini')",
    )
    instrument_type: str | None = Field(
        default=None,
        description="(Optional) Filter by instrument type (e.g., 'Spectrometer', 'Imager', 'Particle Detector')",
    )
    limit: int = Field(default=10, description="(Optional, default: 10) Maximum number of results to return")


class PDS4SearchInstrumentsOutput(OutputSchema):
    """Output schema for PDS4 search instruments tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    instruments: list[dict] = Field(..., description="List of instrument results")


@mcp_tool
class PDS4SearchInstrumentsTool(BaseTool[PDS4SearchInstrumentsInput, PDS4SearchInstrumentsOutput]):
    """Search PDS Context products that are Instruments.

    Instruments are scientific devices (cameras, spectrometers, etc.) used on spacecraft to collect data.
    Example: Cassini RADAR - urn:nasa:pds:context:instrument:radar.cassini

    Use for queries about specific instruments, instrument types, or instruments on missions/spacecraft.
    """

    input_schema = PDS4SearchInstrumentsInput
    output_schema = PDS4SearchInstrumentsOutput

    async def _arun(self, params: PDS4SearchInstrumentsInput) -> PDS4SearchInstrumentsOutput:
        """Execute PDS4 instrument search."""
        async with PDS4Client() as client:
            response: PDS4SearchResponse = await client.search_context_instruments(
                keywords=params.keywords,
                instrument_type=params.instrument_type,
                limit=params.limit,
            )

            instruments = []
            for instrument in response.data:
                instrument_data = {
                    "id": instrument.id,
                    "lid": instrument.lid,
                    "lidvid": instrument.lidvid,
                    "title": instrument.title,
                }

                if instrument.instrument:
                    instrument_data["instrument"] = instrument.instrument.model_dump(exclude_none=True)

                instruments.append(instrument_data)

            return PDS4SearchInstrumentsOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit,
                instruments=instruments,
            )
