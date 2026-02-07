"""PDS4 search instrument hosts tool for finding spacecraft and rovers."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import PDS4InstrumentHost, PDS4SearchResponse


class PDS4SearchInstrumentHostsInput(InputSchema):
    """Input schema for PDS4 search instrument hosts tool."""

    keywords: str | None = Field(
        default=None,
        description="(Optional) Search terms for instrument hosts (e.g., 'mars rover', 'voyager spacecraft')",
    )
    instrument_host_type: str | None = Field(
        default=None, description="(Optional) Filter by type (e.g., 'Rover', 'Spacecraft', 'Lander')"
    )
    limit: int = Field(default=10, description="(Optional, default: 10) Maximum number of results to return")


class PDS4InstrumentHostResult(OutputSchema):
    """Result model for a single instrument host in search results."""

    id: str = Field(..., description="The instrument host identifier")
    lid: str | None = Field(default=None, description="Logical identifier")
    lidvid: str | None = Field(default=None, description="Logical identifier with version")
    title: str | None = Field(default=None, description="Instrument host title")
    instrument_host: PDS4InstrumentHost | None = Field(default=None, description="Instrument host details")


class PDS4SearchInstrumentHostsOutput(OutputSchema):
    """Output schema for PDS4 search instrument hosts tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    instrument_hosts: list[PDS4InstrumentHostResult] = Field(..., description="List of instrument host results")


@mcp_tool
class PDS4SearchInstrumentHostsTool(BaseTool[PDS4SearchInstrumentHostsInput, PDS4SearchInstrumentHostsOutput]):
    """Search PDS Context products that are Instrument Hosts (spacecraft, rovers, telescopes).

    Instrument Hosts are platforms that carry scientific instruments: spacecraft, rovers, landers, telescopes.
    Example: Cassini Orbiter - urn:nasa:pds:context:instrument_host:spacecraft.cassini

    Use for queries about specific spacecraft, rovers, or platforms that carry instruments.
    """

    input_schema = PDS4SearchInstrumentHostsInput
    output_schema = PDS4SearchInstrumentHostsOutput

    async def _arun(self, params: PDS4SearchInstrumentHostsInput) -> PDS4SearchInstrumentHostsOutput:
        """Execute PDS4 instrument host search."""
        async with PDS4Client() as client:
            response: PDS4SearchResponse = await client.search_context_instrument_hosts(
                keywords=params.keywords,
                instrument_host_type=params.instrument_host_type,
                limit=params.limit,
            )

            instrument_hosts = [
                PDS4InstrumentHostResult(
                    id=host.id,
                    lid=host.lid,
                    lidvid=host.lidvid,
                    title=host.title,
                    instrument_host=host.instrument_host,
                )
                for host in response.data
            ]

            return PDS4SearchInstrumentHostsOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit,
                instrument_hosts=instrument_hosts,
            )
