"""IMG Atlas search products tool for querying planetary imagery."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.img.client import IMGAtlasClient


class IMGImageSize(OutputSchema):
    """Image dimensions for a product."""

    lines: int = Field(..., description="Number of lines (height) in the image")
    samples: int = Field(..., description="Number of samples (width) per line")


class IMGProductResult(OutputSchema):
    """Single product result from a search."""

    uuid: str = Field(..., description="Unique identifier for the product")
    target: str = Field(..., description="Target body (e.g., 'Mars', 'Saturn')")
    mission: str = Field(..., description="Mission name")
    spacecraft: str = Field(..., description="Spacecraft name")
    instrument: str = Field(..., description="Instrument name")
    product_type: str = Field(..., description="Product type (EDR for raw, RDR for processed)")
    start_time: str | None = Field(default=None, description="Start time of observation (ISO 8601)")
    stop_time: str | None = Field(default=None, description="Stop time of observation (ISO 8601)")
    sol: int | None = Field(default=None, description="Mars day number (sol) if applicable")
    image_size: IMGImageSize | None = Field(default=None, description="Image dimensions")
    data_url: str | None = Field(default=None, description="URL to product data file")
    label_url: str | None = Field(default=None, description="URL to PDS label file")
    browse_url: str | None = Field(default=None, description="URL to browse (full resolution) image")
    thumbnail_url: str | None = Field(default=None, description="URL to thumbnail image")


class IMGSearchProductsInput(InputSchema):
    """Input schema for IMG Atlas search products tool."""

    target: str | None = Field(
        default=None, description="(Optional) Target body (e.g., 'Mars', 'Saturn', 'Moon'). Case-insensitive."
    )
    mission: str | None = Field(
        default=None,
        description="(Optional) Mission name filter (e.g., 'MSL', 'MER', 'Cassini'). Partial match with wildcards.",
    )
    instrument: str | None = Field(
        default=None,
        description="(Optional) Instrument name filter (e.g., 'HAZCAM', 'MASTCAM', 'ISS'). Partial match with wildcards.",
    )
    spacecraft: str | None = Field(
        default=None,
        description="(Optional) Spacecraft name filter (e.g., 'CURIOSITY', 'SPIRIT', 'CASSINI ORBITER')",
    )
    start_time: str | None = Field(
        default=None,
        description="(Optional) Start of time range (ISO 8601 format, e.g., '2020-01-01T00:00:00Z')",
    )
    stop_time: str | None = Field(default=None, description="(Optional) End of time range (ISO 8601 format)")
    sol_min: int | None = Field(default=None, description="(Optional) Minimum sol number for Mars missions (e.g., 1)")
    sol_max: int | None = Field(default=None, description="(Optional) Maximum sol number for Mars missions (e.g., 100)")
    product_type: str | None = Field(
        default=None,
        description="(Optional) Product type filter ('EDR' for raw data, 'RDR' for processed data)",
    )
    filter_name: str | None = Field(
        default=None,
        description="(Optional) Camera filter name (e.g., 'L0', 'R0', 'RED', 'GREEN', 'BLUE')",
    )
    frame_type: str | None = Field(default=None, description="(Optional) Frame type filter (e.g., 'FULL', 'SUBFRAME')")
    exposure_min: float | None = Field(default=None, description="(Optional) Minimum exposure duration in milliseconds")
    exposure_max: float | None = Field(default=None, description="(Optional) Maximum exposure duration in milliseconds")
    local_solar_time: str | None = Field(
        default=None,
        description="(Optional) Local true solar time filter (e.g., '12:00' for noon images)",
    )
    sort_by: str | None = Field(
        default=None,
        description="(Optional) Field to sort by ('START_TIME', 'PLANET_DAY_NUMBER', 'EXPOSURE_DURATION')",
    )
    sort_order: str = Field(
        default="desc",
        description="(Optional) Sort direction ('asc' or 'desc', default 'desc')",
    )
    rows: int = Field(default=100, description="(Optional) Maximum number of products to return (default 100)")
    start: int = Field(default=0, description="(Optional) Pagination offset (default 0)")


class IMGSearchProductsOutput(OutputSchema):
    """Output schema for IMG Atlas search products tool."""

    status: str = Field(..., description="Status of the search ('success' or 'error')")
    num_found: int = Field(..., description="Total number of products matching the criteria")
    start: int = Field(..., description="Pagination offset used")
    query_time_ms: int = Field(..., description="Query execution time in milliseconds")
    products: list[IMGProductResult] = Field(..., description="List of matching products with metadata and URLs")
    error: str | None = Field(default=None, description="Error message if status is 'error'")


@mcp_tool
class IMGSearchProductsTool(BaseTool[IMGSearchProductsInput, IMGSearchProductsOutput]):
    """Search for planetary imagery in the PDS Imaging Node Atlas archive.

    The Atlas archive contains 30+ million images from Mars rovers (Spirit, Opportunity,
    Curiosity, Perseverance), Cassini, Voyager, LRO, and MESSENGER.

    Use IMGGetFacetsTool to dynamically discover available targets, missions, and instruments.
    """

    input_schema = IMGSearchProductsInput
    output_schema = IMGSearchProductsOutput

    async def _arun(self, params: IMGSearchProductsInput) -> IMGSearchProductsOutput:
        """Execute IMG Atlas product search."""
        async with IMGAtlasClient() as client:
            # Build sort parameter
            sort_param = None
            if params.sort_by:
                order = params.sort_order if params.sort_order in ("asc", "desc") else "desc"
                sort_param = f"{params.sort_by} {order}"

            response = await client.search_products(
                target=params.target,
                mission=params.mission,
                instrument=params.instrument,
                spacecraft=params.spacecraft,
                start_time=params.start_time,
                stop_time=params.stop_time,
                sol_min=params.sol_min,
                sol_max=params.sol_max,
                product_type=params.product_type,
                filter_name=params.filter_name,
                frame_type=params.frame_type,
                exposure_min=params.exposure_min,
                exposure_max=params.exposure_max,
                local_solar_time=params.local_solar_time,
                rows=params.rows,
                start=params.start,
                sort=sort_param,
            )

            if response.status == "error":
                return IMGSearchProductsOutput(
                    status="error",
                    num_found=0,
                    start=0,
                    query_time_ms=0,
                    products=[],
                    error=response.error,
                )

            products = []
            for product in response.products:
                # Build image size if available
                image_size = None
                if product.lines is not None and product.line_samples is not None:
                    image_size = IMGImageSize(
                        lines=product.lines,
                        samples=product.line_samples,
                    )

                # Build product result
                product_result = IMGProductResult(
                    uuid=product.uuid,
                    target=product.target,
                    mission=product.mission_name,
                    spacecraft=product.spacecraft_name,
                    instrument=product.instrument_name,
                    product_type=product.product_type,
                    start_time=product.start_time,
                    stop_time=product.stop_time,
                    sol=product.planet_day_number,
                    image_size=image_size,
                    data_url=product.data_url,
                    label_url=product.label_url,
                    browse_url=product.browse_url,
                    thumbnail_url=product.thumbnail_url,
                )
                products.append(product_result)

            return IMGSearchProductsOutput(
                status="success",
                num_found=response.num_found,
                start=response.start,
                query_time_ms=response.query_time_ms,
                products=products,
            )
