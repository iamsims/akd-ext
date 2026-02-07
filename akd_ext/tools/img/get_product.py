"""IMG Atlas get product tool for retrieving detailed product metadata."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.img.client import IMGAtlasClient


class IMGProductUrls(OutputSchema):
    """Download URLs for a product."""

    data: str | None = Field(default=None, description="URL to product data file")
    label: str | None = Field(default=None, description="URL to PDS label file")
    browse: str | None = Field(default=None, description="URL to browse (full resolution) image")
    thumbnail: str | None = Field(default=None, description="URL to thumbnail image")


class IMGProductDetail(OutputSchema):
    """Detailed metadata for a single product."""

    uuid: str = Field(..., description="Unique identifier for the product")
    product_id: str = Field(..., description="Product identifier")
    pds_standard: str = Field(..., description="PDS standard version (PDS3 or PDS4)")
    target: str = Field(..., description="Target body (e.g., 'Mars', 'Saturn')")
    product_type: str = Field(..., description="Product type (EDR for raw, RDR for processed)")
    mission: str = Field(..., description="Mission name")
    spacecraft: str = Field(..., description="Spacecraft name")
    instrument: str = Field(..., description="Instrument name")
    start_time: str | None = Field(default=None, description="Start time of observation (ISO 8601)")
    stop_time: str | None = Field(default=None, description="Stop time of observation (ISO 8601)")
    product_creation_time: str | None = Field(default=None, description="Product creation time (ISO 8601)")
    sol: int | None = Field(default=None, description="Mars day number (sol) if applicable")
    local_solar_time: str | None = Field(default=None, description="Local true solar time on the target")
    solar_azimuth: float | None = Field(default=None, description="Solar azimuth angle in degrees")
    solar_elevation: float | None = Field(default=None, description="Solar elevation angle in degrees")
    lines: int | None = Field(default=None, description="Number of lines (height) in the image")
    line_samples: int | None = Field(default=None, description="Number of samples (width) per line")
    exposure_duration_ms: float | None = Field(default=None, description="Exposure duration in milliseconds")
    compression_ratio: float | None = Field(default=None, description="Compression ratio if compressed")
    frame_type: str | None = Field(default=None, description="Frame type (FULL, SUBFRAME)")
    center_latitude: float | None = Field(default=None, description="Center latitude of the image in degrees")
    center_longitude: float | None = Field(default=None, description="Center longitude of the image in degrees")
    urls: IMGProductUrls = Field(..., description="Download URLs for the product")


class IMGGetProductInput(InputSchema):
    """Input schema for IMG Atlas get product tool."""

    product_id: str = Field(..., description="Product identifier (uuid or PRODUCT_ID)")


class IMGGetProductOutput(OutputSchema):
    """Output schema for IMG Atlas get product tool."""

    status: str = Field(..., description="Status of the operation ('success', 'not_found', or 'error')")
    product: IMGProductDetail | None = Field(default=None, description="Full product metadata if found")
    message: str | None = Field(default=None, description="Status message")
    error: str | None = Field(default=None, description="Error message if status is 'error'")


@mcp_tool
class IMGGetProductTool(BaseTool[IMGGetProductInput, IMGGetProductOutput]):
    """Get detailed metadata for a specific imagery product by ID.

    Returns comprehensive information including time, location, imaging parameters,
    solar geometry, and download URLs for the product data, label, browse image,
    and thumbnail.
    """

    input_schema = IMGGetProductInput
    output_schema = IMGGetProductOutput

    async def _arun(self, params: IMGGetProductInput) -> IMGGetProductOutput:
        """Execute IMG Atlas get product."""
        async with IMGAtlasClient() as client:
            response = await client.get_product(params.product_id)

            if response.status == "error":
                return IMGGetProductOutput(
                    status="error",
                    error=response.error,
                )

            if not response.products:
                return IMGGetProductOutput(
                    status="not_found",
                    message=f"Product '{params.product_id}' not found",
                )

            product = response.products[0]

            # Build URLs object
            urls = IMGProductUrls(
                data=product.data_url,
                label=product.label_url,
                browse=product.browse_url,
                thumbnail=product.thumbnail_url,
            )

            # Build comprehensive product metadata
            product_detail = IMGProductDetail(
                uuid=product.uuid,
                product_id=product.product_id,
                pds_standard=product.pds_standard,
                target=product.target,
                product_type=product.product_type,
                mission=product.mission_name,
                spacecraft=product.spacecraft_name,
                instrument=product.instrument_name,
                start_time=product.start_time,
                stop_time=product.stop_time,
                product_creation_time=product.product_creation_time,
                sol=product.planet_day_number,
                local_solar_time=product.local_true_solar_time,
                solar_azimuth=product.solar_azimuth,
                solar_elevation=product.solar_elevation,
                lines=product.lines,
                line_samples=product.line_samples,
                exposure_duration_ms=product.exposure_duration,
                compression_ratio=product.compression_ratio,
                frame_type=product.frame_type,
                center_latitude=product.center_latitude,
                center_longitude=product.center_longitude,
                urls=urls,
            )

            return IMGGetProductOutput(
                status="success",
                product=product_detail,
            )
