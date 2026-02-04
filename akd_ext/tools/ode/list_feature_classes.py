"""ODE list feature classes tool for discovering available feature types."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.ode.client import ODEClient


class ODEListFeatureClassesInput(InputSchema):
    """Input schema for ODE list feature classes tool."""

    target: str = Field(..., description="Planetary body (mars, moon, mercury, phobos, deimos, venus)")


class ODEListFeatureClassesOutput(OutputSchema):
    """Output schema for ODE list feature classes tool."""

    status: str = Field(..., description="Response status (SUCCESS or ERROR)")
    feature_classes: list[str] = Field(..., description="List of available feature types")
    error: str | None = Field(default=None, description="Error message if status is ERROR")


@mcp_tool
class ODEListFeatureClassesTool(BaseTool[ODEListFeatureClassesInput, ODEListFeatureClassesOutput]):
    """List available feature types (classes) for a planetary target.

    This tool returns the types of named geographic features available for a given planetary body,
    such as craters, mountains (mons), valleys (vallis), plains (planitia), and other landforms.

    Use this tool to discover what types of features are cataloged before looking up specific features.
    """

    input_schema = ODEListFeatureClassesInput
    output_schema = ODEListFeatureClassesOutput

    async def _arun(self, params: ODEListFeatureClassesInput) -> ODEListFeatureClassesOutput:
        """Execute ODE list feature classes query."""
        async with ODEClient() as client:
            response = await client.list_feature_classes(target=params.target)

            return ODEListFeatureClassesOutput(
                status=response.status,
                feature_classes=response.feature_classes,
                error=response.error,
            )
