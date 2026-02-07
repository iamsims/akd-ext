"""ODE get feature bounds tool for looking up geographic bounds of named planetary features."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.ode.client import ODEClient


class ODEFeatureBoundResult(OutputSchema):
    """Model for a feature with geographic bounds."""

    feature_class: str = Field(..., description="Type of feature (e.g., crater, chasma, mons)")
    feature_name: str = Field(..., description="Name of the feature")
    min_lat: float = Field(..., description="Minimum latitude of the feature in degrees")
    max_lat: float = Field(..., description="Maximum latitude of the feature in degrees")
    west_lon: float = Field(..., description="Westernmost longitude of the feature in degrees")
    east_lon: float = Field(..., description="Easternmost longitude of the feature in degrees")


class ODEGetFeatureBoundsInput(InputSchema):
    """Input schema for ODE get feature bounds tool."""

    target: str = Field(..., description="Planetary body (mars, moon, mercury, phobos, deimos, venus)")
    feature_class: str = Field(..., description="Feature type (e.g., crater, chasma, mons, vallis, mare)")
    feature_name: str = Field(..., description="Name of the feature (e.g., Gale, Jezero, Olympus Mons)")


class ODEGetFeatureBoundsOutput(OutputSchema):
    """Output schema for ODE get feature bounds tool."""

    status: str = Field(..., description="Response status (SUCCESS or ERROR)")
    count: int = Field(..., description="Number of features found")
    features: list[ODEFeatureBoundResult] = Field(..., description="List of features with geographic bounds")
    error: str | None = Field(default=None, description="Error message if status is ERROR")


@mcp_tool
class ODEGetFeatureBoundsTool(BaseTool[ODEGetFeatureBoundsInput, ODEGetFeatureBoundsOutput]):
    """Get latitude/longitude bounds for named planetary features.

    This tool looks up the geographic bounding box for specific named features on planetary bodies,
    such as craters, mountains, valleys, and other landmarks. The bounds can be used to filter
    product searches by geographic region.

    Use this tool to get coordinates for features of interest before searching for data products.
    """

    input_schema = ODEGetFeatureBoundsInput
    output_schema = ODEGetFeatureBoundsOutput

    async def _arun(self, params: ODEGetFeatureBoundsInput) -> ODEGetFeatureBoundsOutput:
        """Execute ODE get feature bounds query."""
        async with ODEClient() as client:
            response = await client.get_feature_bounds(
                target=params.target,
                feature_class=params.feature_class,
                feature_name=params.feature_name,
            )

            features = []
            for feature in response.features:
                features.append(
                    ODEFeatureBoundResult(
                        feature_class=feature.feature_class,
                        feature_name=feature.feature_name,
                        min_lat=feature.min_lat,
                        max_lat=feature.max_lat,
                        west_lon=feature.west_lon,
                        east_lon=feature.east_lon,
                    )
                )

            return ODEGetFeatureBoundsOutput(
                status=response.status,
                count=response.count,
                features=features,
                error=response.error,
            )
