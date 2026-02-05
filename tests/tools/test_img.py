"""Tests for IMG Atlas tools."""

import pytest

from akd_ext.tools.img import (
    IMGCountProductsInput,
    IMGCountProductsTool,
    IMGGetFacetsInput,
    IMGGetFacetsTool,
    IMGGetProductInput,
    IMGGetProductTool,
    IMGSearchProductsInput,
    IMGSearchProductsTool,
)


@pytest.mark.asyncio
async def test_img_search_products():
    """Test IMG search products tool."""
    tool = IMGSearchProductsTool()
    input_data = IMGSearchProductsInput(target="Mars", mission="MSL", rows=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.num_found >= 0
    assert isinstance(result.products, list)
    assert result.query_time_ms >= 0


@pytest.mark.asyncio
async def test_img_search_products_with_sol():
    """Test IMG search products with sol range."""
    tool = IMGSearchProductsTool()
    input_data = IMGSearchProductsInput(target="Mars", mission="MSL", sol_min=1, sol_max=10, rows=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.num_found >= 0
    assert isinstance(result.products, list)


@pytest.mark.asyncio
async def test_img_search_products_with_instrument():
    """Test IMG search products with instrument filter."""
    tool = IMGSearchProductsTool()
    input_data = IMGSearchProductsInput(target="Mars", instrument="MASTCAM", rows=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.num_found >= 0
    assert isinstance(result.products, list)


@pytest.mark.asyncio
async def test_img_count_products():
    """Test IMG count products tool."""
    tool = IMGCountProductsTool()
    input_data = IMGCountProductsInput(target="Mars", mission="MSL")

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count >= 0
    assert result.query_time_ms >= 0
    assert isinstance(result.filters, dict)


@pytest.mark.asyncio
async def test_img_count_products_with_filters():
    """Test IMG count products with multiple filters."""
    tool = IMGCountProductsTool()
    input_data = IMGCountProductsInput(target="Mars", mission="MSL", instrument="MASTCAM", product_type="EDR")

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count >= 0
    assert result.filters["target"] == "Mars"
    assert result.filters["mission"] == "MSL"
    assert result.filters["instrument"] == "MASTCAM"


@pytest.mark.asyncio
async def test_img_get_facets_targets():
    """Test IMG get facets tool for targets."""
    tool = IMGGetFacetsTool()
    input_data = IMGGetFacetsInput(facet_field="TARGET", limit=20)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.facet_field == "TARGET"
    assert result.count > 0
    assert isinstance(result.values, list)
    assert result.query_time_ms >= 0
    # Check that values are sorted by count (descending)
    if len(result.values) > 1:
        assert result.values[0]["count"] >= result.values[1]["count"]


@pytest.mark.asyncio
async def test_img_get_facets_missions():
    """Test IMG get facets tool for missions."""
    tool = IMGGetFacetsTool()
    input_data = IMGGetFacetsInput(facet_field="ATLAS_MISSION_NAME", limit=20)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.facet_field == "ATLAS_MISSION_NAME"
    assert result.count > 0
    assert isinstance(result.values, list)


@pytest.mark.asyncio
async def test_img_get_facets_instruments():
    """Test IMG get facets tool for instruments."""
    tool = IMGGetFacetsTool()
    input_data = IMGGetFacetsInput(facet_field="ATLAS_INSTRUMENT_NAME", limit=20, target="Mars")

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.facet_field == "ATLAS_INSTRUMENT_NAME"
    assert result.count > 0
    assert isinstance(result.values, list)


@pytest.mark.asyncio
async def test_img_get_product():
    """Test IMG get product tool.

    First search for a product, then retrieve its details.
    """
    # First, search for a product to get an ID
    search_tool = IMGSearchProductsTool()
    search_input = IMGSearchProductsInput(target="Mars", mission="MSL", rows=1)
    search_result = await search_tool.arun(search_input)

    # Skip if no products found
    if search_result.num_found == 0 or not search_result.products:
        pytest.skip("No products found to test get_product")

    # Get the product ID
    product_id = search_result.products[0].get("uuid")
    if not product_id:
        pytest.skip("Product UUID not available")

    # Now test get_product
    tool = IMGGetProductTool()
    input_data = IMGGetProductInput(product_id=product_id)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.product is not None
    assert isinstance(result.product, dict)
    assert result.product.get("uuid") == product_id


@pytest.mark.asyncio
async def test_img_get_product_not_found():
    """Test IMG get product tool with non-existent ID."""
    tool = IMGGetProductTool()
    input_data = IMGGetProductInput(product_id="nonexistent-id-12345")

    result = await tool.arun(input_data)

    assert result.status == "not_found"
    assert result.message is not None


@pytest.mark.asyncio
async def test_img_search_products_pagination():
    """Test IMG search products with pagination."""
    tool = IMGSearchProductsTool()
    input_data = IMGSearchProductsInput(target="Mars", rows=5, start=0)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.start == 0
    assert len(result.products) <= 5


@pytest.mark.asyncio
async def test_img_search_products_sorting():
    """Test IMG search products with sorting."""
    tool = IMGSearchProductsTool()
    input_data = IMGSearchProductsInput(target="Mars", mission="MSL", rows=5, sort_by="START_TIME", sort_order="desc")

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert isinstance(result.products, list)
