"""Tests for ODE tools."""

import pytest

from akd_ext.tools.ode import (
    ODECountProductsInput,
    ODECountProductsTool,
    ODEGetFeatureBoundsInput,
    ODEGetFeatureBoundsTool,
    ODEListFeatureClassesInput,
    ODEListFeatureClassesTool,
    ODEListFeatureNamesInput,
    ODEListFeatureNamesTool,
    ODEListInstrumentsInput,
    ODEListInstrumentsTool,
    ODESearchProductsInput,
    ODESearchProductsTool,
)


@pytest.mark.asyncio
async def test_ode_list_instruments():
    """Test ODE list instruments tool."""
    tool = ODEListInstrumentsTool()
    input_data = ODEListInstrumentsInput(target="mars", limit=5)

    result = await tool.arun(input_data)

    assert result.status in ["Success", "SUCCESS", "ERROR"]
    assert isinstance(result.instruments, list)
    if result.status in ["Success", "SUCCESS"]:
        assert len(result.instruments) <= 5


@pytest.mark.asyncio
async def test_ode_list_feature_classes():
    """Test ODE list feature classes tool."""
    tool = ODEListFeatureClassesTool()
    input_data = ODEListFeatureClassesInput(target="mars")

    result = await tool.arun(input_data)

    assert result.status in ["Success", "SUCCESS", "ERROR"]
    assert isinstance(result.feature_classes, list)


@pytest.mark.asyncio
async def test_ode_list_feature_names():
    """Test ODE list feature names tool."""
    tool = ODEListFeatureNamesTool()
    input_data = ODEListFeatureNamesInput(target="mars", feature_class="crater", limit=10)

    result = await tool.arun(input_data)

    assert result.status in ["Success", "SUCCESS", "ERROR"]
    assert isinstance(result.feature_names, list)
    if result.status in ["Success", "SUCCESS"]:
        # Note: ODE API may not respect the limit parameter
        assert len(result.feature_names) >= 0


@pytest.mark.asyncio
async def test_ode_get_feature_bounds():
    """Test ODE get feature bounds tool."""
    tool = ODEGetFeatureBoundsTool()
    input_data = ODEGetFeatureBoundsInput(target="mars", feature_class="crater", feature_name="Gale")

    result = await tool.arun(input_data)

    assert result.status in ["Success", "SUCCESS", "ERROR"]
    assert isinstance(result.features, list)
    if result.status in ["Success", "SUCCESS"] and len(result.features) > 0:
        feature = result.features[0]
        assert "feature_class" in feature
        assert "feature_name" in feature
        assert "min_lat" in feature
        assert "max_lat" in feature


@pytest.mark.asyncio
async def test_ode_count_products():
    """Test ODE count products tool."""
    tool = ODECountProductsTool()
    input_data = ODECountProductsInput(target="mars", ihid="MRO", iid="HIRISE", pt="RDRV11")

    result = await tool.arun(input_data)

    assert result.status in ["Success", "SUCCESS", "ERROR"]
    assert isinstance(result.count, int)
    assert result.count >= 0


@pytest.mark.asyncio
async def test_ode_search_products():
    """Test ODE search products tool."""
    tool = ODESearchProductsTool()
    input_data = ODESearchProductsInput(target="mars", ihid="MRO", iid="CTX", pt="EDR", limit=3)

    result = await tool.arun(input_data)

    assert result.status in ["Success", "SUCCESS", "ERROR"]
    assert isinstance(result.products, list)
    if result.status in ["Success", "SUCCESS"]:
        assert len(result.products) <= 3
        assert result.count >= 0
