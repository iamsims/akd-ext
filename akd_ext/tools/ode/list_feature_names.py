"""ODE list feature names tool for discovering named features by type."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.ode.client import ODEClient


class ODEListFeatureNamesInput(InputSchema):
    """Input schema for ODE list feature names tool."""

    target: str = Field(..., description="Planetary body (mars, moon, mercury, phobos, deimos, venus)")
    feature_class: str = Field(..., description="Feature type (e.g., crater, chasma, mons, vallis, mare)")
    limit: int = Field(default=50, description="(Optional, default: 50) Maximum number of feature names to return")


class ODEListFeatureNamesOutput(OutputSchema):
    """Output schema for ODE list feature names tool."""

    status: str = Field(..., description="Response status (SUCCESS or ERROR)")
    feature_names: list[str] = Field(..., description="List of feature names")
    error: str | None = Field(default=None, description="Error message if status is ERROR")


@mcp_tool
class ODEListFeatureNamesTool(BaseTool[ODEListFeatureNamesInput, ODEListFeatureNamesOutput]):
    """List names of features for a specific feature type on a planetary target.

    This tool returns the names of specific geographic features of a given type,
    such as all craters, mountains, or valleys on a planetary body.

    Use this tool to discover specific named features before looking up their bounds.
    """

    input_schema = ODEListFeatureNamesInput
    output_schema = ODEListFeatureNamesOutput

    async def _arun(self, params: ODEListFeatureNamesInput) -> ODEListFeatureNamesOutput:
        """Execute ODE list feature names query."""
        async with ODEClient() as client:
            response = await client.list_feature_names(
                target=params.target,
                feature_class=params.feature_class,
                limit=params.limit,
            )

            return ODEListFeatureNamesOutput(
                status=response.status,
                feature_names=response.feature_names,
                error=response.error,
            )
