"""PDS4 search collections tool for finding data collections by context references."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import PDS4SearchResponse


class PDS4SearchCollectionsInput(InputSchema):
    """Input schema for PDS4 search collections tool."""

    ref_lid_instrument: str | None = Field(
        default=None,
        description="(Optional) URN identifier for instrument (e.g., 'urn:nasa:pds:context:instrument:mars2020.mastcamz')",
    )
    ref_lid_target: str | None = Field(
        default=None,
        description="(Optional) URN identifier for target (e.g., 'urn:nasa:pds:context:target:planet.mars')",
    )
    ref_lid_instrument_host: str | None = Field(
        default=None,
        description="(Optional) URN identifier for instrument host (e.g., 'urn:nasa:pds:context:instrument_host:spacecraft.mars2020')",
    )
    ref_lid_investigation: str | None = Field(
        default=None,
        description="(Optional) URN identifier for investigation (e.g., 'urn:nasa:pds:context:investigation:mission.mars2020')",
    )
    start_time: str | None = Field(
        default=None, description="(Optional) Start of time range (ISO 8601 format, e.g., '2020-01-01T00:00:00Z')"
    )
    end_time: str | None = Field(default=None, description="(Optional) End of time range (ISO 8601 format)")
    processing_level: str | None = Field(
        default=None, description='(Optional) Filter by processing level ("Raw", "Calibrated", "Derived")'
    )
    limit: int = Field(default=10, description="(Optional, default: 10) Maximum number of results to return")


class PDS4SearchCollectionsOutput(OutputSchema):
    """Output schema for PDS4 search collections tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    collections: list[dict] = Field(..., description="List of collection results")


@mcp_tool
class PDS4SearchCollectionsTool(BaseTool[PDS4SearchCollectionsInput, PDS4SearchCollectionsOutput]):
    """Search PDS data collections filtered by instrument, target, instrument host, or investigation.

    Example: Mars Reconnaissance Orbiter HiRISE data collections targeting Mars.

    Use for finding data collections associated with specific instruments, targets, spacecraft, or missions.
    """

    input_schema = PDS4SearchCollectionsInput
    output_schema = PDS4SearchCollectionsOutput

    async def _arun(self, params: PDS4SearchCollectionsInput) -> PDS4SearchCollectionsOutput:
        """Execute PDS4 collection search."""
        async with PDS4Client() as client:
            response: PDS4SearchResponse = await client.search_context_collections(
                ref_lid_instrument=params.ref_lid_instrument,
                ref_lid_target=params.ref_lid_target,
                ref_lid_instrument_host=params.ref_lid_instrument_host,
                ref_lid_investigation=params.ref_lid_investigation,
                start_time=params.start_time,
                end_time=params.end_time,
                processing_level=params.processing_level,
                limit=params.limit,
            )

            collections = []
            for collection in response.data:
                collection_data = {
                    "id": collection.id,
                    "lid": collection.lid,
                    "lidvid": collection.lidvid,
                    "title": collection.title,
                    "ref_lid_instrument": collection.ref_lid_instrument,
                    "ref_lid_target": collection.ref_lid_target,
                    "ref_lid_instrument_host": collection.ref_lid_instrument_host,
                    "ref_lid_investigation": collection.ref_lid_investigation,
                }

                if collection.time_coordinates:
                    collection_data["time_coordinates"] = collection.time_coordinates.model_dump(exclude_none=True)
                if collection.primary_result_summary:
                    collection_data["primary_result_summary"] = collection.primary_result_summary.model_dump(
                        exclude_none=True
                    )
                if collection.label_file_info:
                    collection_data["label_file_info"] = collection.label_file_info.model_dump(exclude_none=True)

                collections.append(collection_data)

            return PDS4SearchCollectionsOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit,
                collections=collections,
            )
