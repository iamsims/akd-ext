"""PDS4 search investigations tool for finding missions and projects."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import PDS4SearchResponse


class PDS4SearchInvestigationsInput(InputSchema):
    """Input schema for PDS4 search investigations tool."""

    keywords: str | None = Field(
        default=None, description="Search terms for investigations (e.g., 'mars rover', 'jupiter cassini')"
    )
    limit: int = Field(default=10, description="Maximum number of results to return")


class PDS4SearchInvestigationsOutput(OutputSchema):
    """Output schema for PDS4 search investigations tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    investigations: list[dict] = Field(..., description="List of investigation results")


@mcp_tool
class PDS4SearchInvestigationsTool(BaseTool[PDS4SearchInvestigationsInput, PDS4SearchInvestigationsOutput]):
    """Search PDS Context products that are Investigations (missions/projects).

    Investigations are organized missions or projects that collect scientific data.
    Example: Cassini-Huygens - urn:nasa:pds:context:investigation:mission.cassini-huygens

    Use for queries about space missions, mission timelines, or finding missions that studied specific targets.
    """

    input_schema = PDS4SearchInvestigationsInput
    output_schema = PDS4SearchInvestigationsOutput

    async def _arun(self, params: PDS4SearchInvestigationsInput) -> PDS4SearchInvestigationsOutput:
        """Execute PDS4 investigation search."""
        async with PDS4Client() as client:
            response: PDS4SearchResponse = await client.search_context_investigations(
                keywords=params.keywords,
                limit=params.limit,
            )

            investigations = []
            for investigation in response.data:
                investigation_data = {
                    "id": investigation.id,
                    "lid": investigation.lid,
                    "lidvid": investigation.lidvid,
                    "title": investigation.title,
                }

                if investigation.investigation:
                    investigation_data["investigation"] = investigation.investigation.model_dump(exclude_none=True)
                if investigation.label_file_info:
                    investigation_data["label_file_info"] = investigation.label_file_info.model_dump(exclude_none=True)

                investigations.append(investigation_data)

            return PDS4SearchInvestigationsOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit,
                investigations=investigations,
            )
