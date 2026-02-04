"""ODE search products tool for searching planetary data products."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.ode.client import ODEClient


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
    products: list[dict] = Field(..., description="List of product results")
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
                product_data = {
                    "pdsid": product.pdsid,
                    "ode_id": product.ode_id,
                    "data_set_id": product.data_set_id,
                    "ihid": product.ihid,
                    "iid": product.iid,
                    "pt": product.pt,
                }

                # Geographic information
                if product.center_latitude is not None:
                    product_data["center_latitude"] = product.center_latitude
                if product.center_longitude is not None:
                    product_data["center_longitude"] = product.center_longitude
                if product.minimum_latitude is not None:
                    product_data["minimum_latitude"] = product.minimum_latitude
                if product.maximum_latitude is not None:
                    product_data["maximum_latitude"] = product.maximum_latitude
                if product.westernmost_longitude is not None:
                    product_data["westernmost_longitude"] = product.westernmost_longitude
                if product.easternmost_longitude is not None:
                    product_data["easternmost_longitude"] = product.easternmost_longitude

                # Temporal information
                if product.observation_time:
                    product_data["observation_time"] = product.observation_time
                if product.utc_start_time:
                    product_data["utc_start_time"] = product.utc_start_time
                if product.utc_stop_time:
                    product_data["utc_stop_time"] = product.utc_stop_time

                # Viewing geometry
                if product.emission_angle is not None:
                    product_data["emission_angle"] = product.emission_angle
                if product.incidence_angle is not None:
                    product_data["incidence_angle"] = product.incidence_angle
                if product.phase_angle is not None:
                    product_data["phase_angle"] = product.phase_angle

                # Resolution
                if product.map_scale is not None:
                    product_data["map_scale"] = product.map_scale

                # URLs
                if product.product_url:
                    product_data["product_url"] = product.product_url
                if product.label_url:
                    product_data["label_url"] = product.label_url

                # Files (limit to first 3 to avoid context bloat)
                if product.product_files:
                    product_data["files"] = [
                        {"file_name": f.file_name, "url": f.url, "description": f.description, "file_type": f.file_type}
                        for f in product.product_files[:3]
                    ]
                    if len(product.product_files) > 3:
                        product_data["files_note"] = f"Showing 3 of {len(product.product_files)} files"

                products.append(product_data)

            return ODESearchProductsOutput(
                status=response.status,
                count=response.count,
                products=products,
                error=response.error,
            )
