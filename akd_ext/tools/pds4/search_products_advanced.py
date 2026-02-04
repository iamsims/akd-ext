"""PDS4 search products advanced tool for finding observational products with advanced filtering."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import PDS4SearchResponse


class PDS4SearchProductsAdvancedInput(InputSchema):
    """Input schema for PDS4 search products advanced tool."""

    keywords: str | None = Field(default=None, description="Search terms for product titles")
    start_time: str | None = Field(
        default=None, description="Start of time range (ISO 8601 format, e.g., '2020-01-01T00:00:00Z')"
    )
    end_time: str | None = Field(default=None, description="End of time range (ISO 8601 format)")
    processing_level: str | None = Field(
        default=None, description='Filter by processing level ("Raw", "Calibrated", "Derived")'
    )
    bbox_north: float | None = Field(default=None, description="North bounding coordinate (latitude, -90 to 90)")
    bbox_south: float | None = Field(default=None, description="South bounding coordinate (latitude, -90 to 90)")
    bbox_east: float | None = Field(default=None, description="East bounding coordinate (longitude, -180 to 360)")
    bbox_west: float | None = Field(default=None, description="West bounding coordinate (longitude, -180 to 360)")
    ref_lid_target: str | None = Field(
        default=None, description="URN identifier for target (e.g., 'urn:nasa:pds:context:target:planet.mars')"
    )
    limit: int = Field(default=100, description="Maximum number of results to return")


class PDS4SearchProductsAdvancedOutput(OutputSchema):
    """Output schema for PDS4 search products advanced tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    query: str | None = Field(..., description="The query that was executed")
    limit: int = Field(..., description="Maximum results requested")
    products: list[dict] = Field(..., description="List of observational product results")


@mcp_tool
class PDS4SearchProductsAdvancedTool(BaseTool[PDS4SearchProductsAdvancedInput, PDS4SearchProductsAdvancedOutput]):
    """Search for observational products with advanced filtering.

    Supports temporal, processing level, and spatial (bounding box) filters.
    Use this tool for complex queries combining multiple filter criteria.

    Example use cases:
    - Find all calibrated Mars surface images from a specific time period
    - Search for data within a geographic bounding box
    - Filter by target and processing level

    Use for advanced searches with multiple filter criteria.
    """

    input_schema = PDS4SearchProductsAdvancedInput
    output_schema = PDS4SearchProductsAdvancedOutput

    async def _arun(self, params: PDS4SearchProductsAdvancedInput) -> PDS4SearchProductsAdvancedOutput:
        """Execute PDS4 advanced product search."""
        async with PDS4Client() as client:
            response: PDS4SearchResponse = await client.search_products_advanced(
                keywords=params.keywords,
                start_time=params.start_time,
                end_time=params.end_time,
                processing_level=params.processing_level,
                bbox_north=params.bbox_north,
                bbox_south=params.bbox_south,
                bbox_east=params.bbox_east,
                bbox_west=params.bbox_west,
                ref_lid_target=params.ref_lid_target,
                limit=params.limit,
            )

            products = []
            for product in response.data:
                product_data = {
                    "id": product.id,
                    "lid": product.lid,
                    "lidvid": product.lidvid,
                    "title": product.title,
                    "ref_lid_target": product.ref_lid_target,
                }

                if product.time_coordinates:
                    product_data["time_coordinates"] = product.time_coordinates.model_dump(exclude_none=True)
                if product.primary_result_summary:
                    product_data["primary_result_summary"] = product.primary_result_summary.model_dump(
                        exclude_none=True
                    )
                # Add bounding coordinates if available from properties
                if "cart:Bounding_Coordinates.cart:north_bounding_coordinate" in product.properties:
                    product_data["bounding_coordinates"] = {
                        "north": product.properties.get("cart:Bounding_Coordinates.cart:north_bounding_coordinate"),
                        "south": product.properties.get("cart:Bounding_Coordinates.cart:south_bounding_coordinate"),
                        "east": product.properties.get("cart:Bounding_Coordinates.cart:east_bounding_coordinate"),
                        "west": product.properties.get("cart:Bounding_Coordinates.cart:west_bounding_coordinate"),
                    }

                products.append(product_data)

            return PDS4SearchProductsAdvancedOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                query=response.summary.q,
                limit=params.limit,
                products=products,
            )
