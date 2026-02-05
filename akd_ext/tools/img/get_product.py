"""IMG Atlas get product tool for retrieving detailed product metadata."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.img.client import IMGAtlasClient


class IMGGetProductInput(InputSchema):
    """Input schema for IMG Atlas get product tool."""

    product_id: str = Field(..., description="Product identifier (uuid or PRODUCT_ID)")


class IMGGetProductOutput(OutputSchema):
    """Output schema for IMG Atlas get product tool."""

    status: str = Field(..., description="Status of the operation ('success', 'not_found', or 'error')")
    product: dict | None = Field(default=None, description="Full product metadata if found")
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

            # Build comprehensive product metadata
            product_data: dict = {
                "uuid": product.uuid,
                "product_id": product.product_id,
                "pds_standard": product.pds_standard,
                "target": product.target,
                "product_type": product.product_type,
                "mission": product.mission_name,
                "spacecraft": product.spacecraft_name,
                "instrument": product.instrument_name,
            }

            # Time information
            if product.start_time:
                product_data["start_time"] = product.start_time
            if product.stop_time:
                product_data["stop_time"] = product.stop_time
            if product.product_creation_time:
                product_data["product_creation_time"] = product.product_creation_time

            # Mars rover specific
            if product.planet_day_number is not None:
                product_data["sol"] = product.planet_day_number
            if product.local_true_solar_time:
                product_data["local_solar_time"] = product.local_true_solar_time

            # Solar geometry
            if product.solar_azimuth is not None:
                product_data["solar_azimuth"] = product.solar_azimuth
            if product.solar_elevation is not None:
                product_data["solar_elevation"] = product.solar_elevation

            # Image properties
            if product.lines is not None:
                product_data["lines"] = product.lines
            if product.line_samples is not None:
                product_data["line_samples"] = product.line_samples
            if product.exposure_duration is not None:
                product_data["exposure_duration_ms"] = product.exposure_duration
            if product.compression_ratio is not None:
                product_data["compression_ratio"] = product.compression_ratio
            if product.frame_type:
                product_data["frame_type"] = product.frame_type

            # Geographic
            if product.center_latitude is not None:
                product_data["center_latitude"] = product.center_latitude
            if product.center_longitude is not None:
                product_data["center_longitude"] = product.center_longitude

            # URLs
            product_data["urls"] = {}
            if product.data_url:
                product_data["urls"]["data"] = product.data_url
            if product.label_url:
                product_data["urls"]["label"] = product.label_url
            if product.browse_url:
                product_data["urls"]["browse"] = product.browse_url
            if product.thumbnail_url:
                product_data["urls"]["thumbnail"] = product.thumbnail_url

            return IMGGetProductOutput(
                status="success",
                product=product_data,
            )
