"""PDS4 search targets tool for finding celestial bodies and phenomena."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import PDS4SearchResponse


class PDS4SearchTargetsInput(InputSchema):
    """Input schema for PDS4 search targets tool."""

    keywords: str | None = Field(
        default=None, description="(Optional) Search terms for targets (e.g., 'jupiter moon', 'asteroid belt')"
    )
    target_type: str | None = Field(
        default=None,
        description="(Optional) Filter by target type (e.g., 'Planet', 'Satellite', 'Asteroid', 'Comet')",
    )
    limit: int = Field(default=10, description="(Optional, default: 10) Maximum number of results to return")


class PDS4SearchTargetsOutput(OutputSchema):
    """Output schema for PDS4 search targets tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    targets: list[dict] = Field(..., description="List of target results")


@mcp_tool
class PDS4SearchTargetsTool(BaseTool[PDS4SearchTargetsInput, PDS4SearchTargetsOutput]):
    """Search PDS Context products that are Targets (celestial bodies, phenomena).

    Targets are objects of scientific study: planets, moons, asteroids, comets, etc.
    Example: Mars - urn:nasa:pds:context:target:planet.mars

    Use for queries about specific celestial bodies, finding targets by type, or targets studied by missions.
    """

    input_schema = PDS4SearchTargetsInput
    output_schema = PDS4SearchTargetsOutput

    async def _arun(self, params: PDS4SearchTargetsInput) -> PDS4SearchTargetsOutput:
        """Execute PDS4 target search."""
        async with PDS4Client() as client:
            response: PDS4SearchResponse = await client.search_context_targets(
                keywords=params.keywords,
                target_type=params.target_type,
                limit=params.limit,
            )

            targets = []
            for target in response.data:
                target_data = {
                    "id": target.id,
                    "lid": target.lid,
                    "lidvid": target.lidvid,
                    "title": target.title,
                }

                if target.target:
                    target_data["target"] = target.target.model_dump(exclude_none=True)
                if target.alias:
                    target_data["alias"] = target.alias.model_dump(exclude_none=True)

                targets.append(target_data)

            return PDS4SearchTargetsOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit,
                targets=targets,
            )
