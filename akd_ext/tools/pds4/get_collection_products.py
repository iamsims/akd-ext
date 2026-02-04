"""PDS4 get collection products tool for retrieving products from a specific collection."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.pds4.client import PDS4Client
from akd_ext.tools.pds4.models import PDS4SearchResponse


class PDS4GetCollectionProductsInput(InputSchema):
    """Input schema for PDS4 get collection products tool."""

    collection_urn: str = Field(
        ...,
        description="URN of the collection from search results (e.g., extracted from search_collections response lidvid field)",
    )
    limit: int = Field(default=100, description="(Optional, default: 100) Number of products to return")


class PDS4GetCollectionProductsOutput(OutputSchema):
    """Output schema for PDS4 get collection products tool."""

    total_hits: int = Field(..., description="Total number of hits")
    query_time_ms: int | None = Field(..., description="Query execution time in milliseconds")
    collection_urn: str = Field(..., description="The collection URN that was queried")
    limit: int = Field(..., description="Maximum results requested")
    products: list[dict] = Field(..., description="List of products in the collection")


@mcp_tool
class PDS4GetCollectionProductsTool(BaseTool[PDS4GetCollectionProductsInput, PDS4GetCollectionProductsOutput]):
    """Get products from a specific PDS4 collection.

    Best Practice: Extract collection_urn from search_collections results, not hardcoded values.

    Typical workflow:
    1. Call search_collections() to discover available collections
    2. Extract 'lidvid' field from interesting collections in the response
    3. Use that lidvid as collection_urn parameter here
    4. Iterate through multiple collections if some are empty

    Use for retrieving actual data products from a collection.
    """

    input_schema = PDS4GetCollectionProductsInput
    output_schema = PDS4GetCollectionProductsOutput

    async def _arun(self, params: PDS4GetCollectionProductsInput) -> PDS4GetCollectionProductsOutput:
        """Execute PDS4 get collection products."""
        async with PDS4Client() as client:
            response: PDS4SearchResponse = await client.get_collection_products(
                collection_urn=params.collection_urn,
                limit=params.limit,
            )

            products = []
            for product in response.data:
                product_data = {
                    "id": product.id,
                    "lid": product.lid,
                    "lidvid": product.lidvid,
                    "title": product.title,
                }

                if product.identification_area:
                    product_data["identification_area"] = product.identification_area.model_dump(exclude_none=True)
                if product.time_coordinates:
                    product_data["time_coordinates"] = product.time_coordinates.model_dump(exclude_none=True)
                if product.data_file_info:
                    product_data["data_file_info"] = product.data_file_info.model_dump(exclude_none=True)
                if product.primary_result_summary:
                    product_data["primary_result_summary"] = product.primary_result_summary.model_dump(
                        exclude_none=True
                    )
                if product.provenance:
                    product_data["provenance"] = product.provenance.model_dump(exclude_none=True)

                products.append(product_data)

            return PDS4GetCollectionProductsOutput(
                total_hits=response.summary.hits,
                query_time_ms=response.summary.took,
                collection_urn=params.collection_urn,
                limit=params.limit,
                products=products,
            )
