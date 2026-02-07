"""ODE search products tool for searching planetary data products."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.ode.client import ODEClient


class ODEProductFileItem(OutputSchema):
    """Model for a product file item."""

    file_name: str = Field(..., description="Name of the file")
    url: str = Field(..., description="URL to access the file")
    description: str = Field(..., description="Description of the file")
    file_type: str = Field(..., description="Type of file (e.g., IMG, LBL, etc.)")


class ODEProductResult(OutputSchema):
    """Model for a product result from ODE search."""

    # Required fields
    pdsid: str = Field(..., description="PDS Product ID")
    ode_id: str = Field(..., description="ODE Product ID")
    data_set_id: str = Field(..., description="Dataset ID")
    ihid: str = Field(..., description="Instrument Host ID")
    iid: str = Field(..., description="Instrument ID")
    pt: str = Field(..., description="Product Type")

    # Optional geographic information
    center_latitude: float | None = Field(default=None, description="Center latitude of the observation")
    center_longitude: float | None = Field(default=None, description="Center longitude of the observation")
    minimum_latitude: float | None = Field(default=None, description="Minimum latitude of the observation")
    maximum_latitude: float | None = Field(default=None, description="Maximum latitude of the observation")
    westernmost_longitude: float | None = Field(default=None, description="Westernmost longitude of the observation")
    easternmost_longitude: float | None = Field(default=None, description="Easternmost longitude of the observation")

    # Optional temporal information
    observation_time: str | None = Field(default=None, description="Observation time in UTC")
    utc_start_time: str | None = Field(default=None, description="UTC start time of observation")
    utc_stop_time: str | None = Field(default=None, description="UTC stop time of observation")

    # Optional viewing geometry
    emission_angle: float | None = Field(default=None, description="Emission angle in degrees")
    incidence_angle: float | None = Field(default=None, description="Incidence angle in degrees")
    phase_angle: float | None = Field(default=None, description="Phase angle in degrees")

    # Optional resolution
    map_scale: float | None = Field(default=None, description="Map scale in meters per pixel")

    # Optional URLs
    product_url: str | None = Field(default=None, description="URL to the product metadata")
    label_url: str | None = Field(default=None, description="URL to the product label file")

    # Optional files
    files: list[ODEProductFileItem] | None = Field(default=None, description="List of product files")
    files_note: str | None = Field(default=None, description="Note about the files (e.g., truncation message)")


class ODESearchProductsInput(InputSchema):
    """Input schema for ODE search products tool."""

    target: str = Field(..., description="Planetary body (mars, moon, mercury, phobos, deimos, venus)")
    ihid: str | None = Field(default=None, description='(Optional) Instrument Host ID (e.g., "MRO", "LRO", "MESS")')
    iid: str | None = Field(default=None, description='(Optional) Instrument ID (e.g., "HIRISE", "CTX", "LROC")')
    pt: str | None = Field(default=None, description='(Optional) Product Type (e.g., "RDRV11", "EDR")')
    pdsid: str | None = Field(default=None, description="(Optional) PDS Product ID for direct lookup")
    minlat: float | None = Field(default=None, description="(Optional) Minimum latitude (-90 to 90)")
    maxlat: float | None = Field(default=None, description="(Optional) Maximum latitude (-90 to 90)")
    westlon: float | None = Field(default=None, description="(Optional) Western longitude")
    eastlon: float | None = Field(default=None, description="(Optional) Eastern longitude")
    minobtime: str | None = Field(
        default=None, description='(Optional) Minimum observation time in UTC format (e.g., "2018-05-01")'
    )
    maxobtime: str | None = Field(
        default=None, description='(Optional) Maximum observation time in UTC format (e.g., "2018-08-31")'
    )
    limit: int = Field(default=10, description="(Optional, default: 10) Maximum products to return (max 100)")
    offset: int = Field(default=0, description="(Optional, default: 0) Pagination offset")


class ODESearchProductsOutput(OutputSchema):
    """Output schema for ODE search products tool."""

    status: str = Field(..., description="Response status (SUCCESS or ERROR)")
    count: int = Field(..., description="Total number of products matching the query")
    products: list[ODEProductResult] = Field(..., description="List of product results")
    error: str | None = Field(default=None, description="Error message if status is ERROR")


@mcp_tool
class ODESearchProductsTool(BaseTool[ODESearchProductsInput, ODESearchProductsOutput]):
    """Search for products in the Orbital Data Explorer (ODE).

    The ODE provides access to NASA's planetary science data archives for Mars, Moon,
    Mercury, and other bodies. This tool searches for specific data products using
    instrument identifiers or PDS Product IDs, with optional geographic and temporal filtering.

    Use this tool to find specific observational data products from planetary missions.
    """

    input_schema = ODESearchProductsInput
    output_schema = ODESearchProductsOutput

    async def _arun(self, params: ODESearchProductsInput) -> ODESearchProductsOutput:
        """Execute ODE product search."""
        async with ODEClient() as client:
            response = await client.search_products(
                target=params.target,
                ihid=params.ihid,
                iid=params.iid,
                pt=params.pt,
                pdsid=params.pdsid,
                minlat=params.minlat,
                maxlat=params.maxlat,
                westlon=params.westlon,
                eastlon=params.eastlon,
                minobtime=params.minobtime,
                maxobtime=params.maxobtime,
                results="fpc",
                limit=min(params.limit, 100),
                offset=params.offset,
            )

            products = []
            for product in response.products:
                # Build files list if available
                files = None
                files_note = None
                if product.product_files:
                    files = [
                        ODEProductFileItem(
                            file_name=f.file_name, url=f.url, description=f.description, file_type=f.file_type
                        )
                        for f in product.product_files[:3]
                    ]
                    if len(product.product_files) > 3:
                        files_note = f"Showing 3 of {len(product.product_files)} files"

                # Build product result
                product_result = ODEProductResult(
                    pdsid=product.pdsid,
                    ode_id=product.ode_id,
                    data_set_id=product.data_set_id,
                    ihid=product.ihid,
                    iid=product.iid,
                    pt=product.pt,
                    center_latitude=product.center_latitude,
                    center_longitude=product.center_longitude,
                    minimum_latitude=product.minimum_latitude,
                    maximum_latitude=product.maximum_latitude,
                    westernmost_longitude=product.westernmost_longitude,
                    easternmost_longitude=product.easternmost_longitude,
                    observation_time=product.observation_time,
                    utc_start_time=product.utc_start_time,
                    utc_stop_time=product.utc_stop_time,
                    emission_angle=product.emission_angle,
                    incidence_angle=product.incidence_angle,
                    phase_angle=product.phase_angle,
                    map_scale=product.map_scale,
                    product_url=product.product_url,
                    label_url=product.label_url,
                    files=files,
                    files_note=files_note,
                )
                products.append(product_result)

            return ODESearchProductsOutput(
                status=response.status,
                count=response.count,
                products=products,
                error=response.error,
            )
