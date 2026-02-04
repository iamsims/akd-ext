"""SBN CATCH list sources tool."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool

from .client import SBNCatchClient
from .models import CatchSource


class SBNListSourcesInput(InputSchema):
    """Input schema for SBN CATCH list sources tool."""

    pass


class SBNListSourcesOutput(OutputSchema):
    """Output schema for SBN CATCH list sources tool."""

    status: str = Field(..., description="Status of the operation (success or error)")
    sources: list[CatchSource] = Field(..., description="List of available CATCH data sources")
    error: str | None = Field(None, description="Error message if operation failed")


@mcp_tool
class SBNListSourcesTool(BaseTool[SBNListSourcesInput, SBNListSourcesOutput]):
    """List available data sources in the SBN CATCH API.

    Returns information about all available survey data sources including
    observation counts, date ranges, and last update times.
    """

    input_schema = SBNListSourcesInput
    output_schema = SBNListSourcesOutput

    async def _arun(self, params: SBNListSourcesInput) -> SBNListSourcesOutput:
        """Execute SBN CATCH list sources."""
        async with SBNCatchClient() as client:
            response = await client.list_sources()

        return SBNListSourcesOutput(
            status=response.status,
            sources=response.sources,
            error=response.error,
        )
