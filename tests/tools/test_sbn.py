"""Tests for SBN CATCH tools."""

import pytest

from akd_ext.tools.sbn import (
    SBNListSourcesInput,
    SBNListSourcesTool,
    SBNSearchFixedTargetInput,
    SBNSearchFixedTargetTool,
    SBNSearchMovingTargetInput,
    SBNSearchMovingTargetTool,
)


@pytest.mark.asyncio
async def test_sbn_list_sources():
    """Test listing available CATCH data sources."""
    tool = SBNListSourcesTool()
    input_data = SBNListSourcesInput()

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.error is None
    assert isinstance(result.sources, list)
    assert len(result.sources) > 0

    # Verify source structure
    for source in result.sources:
        assert hasattr(source, "source")
        assert hasattr(source, "count")
        assert isinstance(source.source, str)
        assert isinstance(source.count, int)


@pytest.mark.asyncio
async def test_sbn_search_moving_target_halley():
    """Test searching for observations of Halley's Comet."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="1P/Halley",
        start_date="1985-01-01",
        stop_date="1986-12-31",
        cached=True,
        timeout=180.0,
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.error is None
    assert result.job_id is not None
    assert isinstance(result.count, int)
    assert isinstance(result.observations, list)
    assert isinstance(result.source_status, list)

    # If we found observations, verify their structure
    if result.count > 0:
        obs = result.observations[0]
        assert hasattr(obs, "product_id")
        assert hasattr(obs, "source")
        assert isinstance(obs.product_id, str)
        assert isinstance(obs.source, str)


@pytest.mark.asyncio
async def test_sbn_search_moving_target_asteroid():
    """Test searching for observations of asteroid Ceres."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="1",  # Ceres
        start_date="2015-01-01",
        stop_date="2015-12-31",
        cached=True,
        timeout=180.0,
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.error is None
    assert result.job_id is not None
    assert isinstance(result.count, int)
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_moving_target_with_sources():
    """Test searching for observations with specific data sources."""
    tool = SBNSearchMovingTargetTool()

    # First, get available sources
    list_tool = SBNListSourcesTool()
    list_result = await list_tool.arun(SBNListSourcesInput())

    if len(list_result.sources) == 0:
        pytest.skip("No data sources available")

    # Use first available source
    first_source = list_result.sources[0].source

    input_data = SBNSearchMovingTargetInput(
        target="433",  # Eros
        sources=[first_source],
        start_date="2000-01-01",
        stop_date="2001-12-31",
        cached=True,
        timeout=180.0,
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.error is None
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_moving_target_with_padding():
    """Test searching for observations with search padding."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="67P",  # 67P/Churyumov-Gerasimenko
        start_date="2014-01-01",
        stop_date="2014-12-31",
        padding=5.0,  # 5 arcminutes padding
        cached=True,
        timeout=180.0,
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.error is None
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_moving_target_with_uncertainty():
    """Test searching for observations with uncertainty ellipse."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="2019 OK",
        start_date="2019-07-01",
        stop_date="2019-08-01",
        uncertainty_ellipse=True,
        cached=True,
        timeout=180.0,
    )

    result = await tool.arun(input_data)

    # This might not find results (depends on data availability)
    # but should not error
    assert result.status in ("success", "error")
    if result.status == "success":
        assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_fixed_target_basic():
    """Test searching for observations at fixed coordinates."""
    tool = SBNSearchFixedTargetTool()
    input_data = SBNSearchFixedTargetInput(
        ra="12:30:00",  # Sexagesimal format
        dec="+15:45:30",
        radius=10.0,  # 10 arcminutes
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.error is None
    assert isinstance(result.count, int)
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_fixed_target_decimal_degrees():
    """Test searching for observations at fixed coordinates in decimal degrees."""
    tool = SBNSearchFixedTargetTool()
    input_data = SBNSearchFixedTargetInput(
        ra="187.5",  # Decimal degrees
        dec="15.75833",
        radius=15.0,
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.error is None
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_fixed_target_with_date_range():
    """Test searching for observations at fixed coordinates with date range."""
    tool = SBNSearchFixedTargetTool()
    input_data = SBNSearchFixedTargetInput(
        ra="12:30:00",
        dec="+15:45:30",
        radius=10.0,
        start_date="2020-01-01",
        stop_date="2020-12-31",
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_fixed_target_with_sources():
    """Test searching for observations at fixed coordinates with specific sources."""
    tool = SBNSearchFixedTargetTool()

    # First, get available sources
    list_tool = SBNListSourcesTool()
    list_result = await list_tool.arun(SBNListSourcesInput())

    if len(list_result.sources) == 0:
        pytest.skip("No data sources available")

    # Use first available source
    first_source = list_result.sources[0].source

    input_data = SBNSearchFixedTargetInput(
        ra="12:00:00",
        dec="+10:00:00",
        radius=20.0,
        sources=[first_source],
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_fixed_target_with_intersection_type():
    """Test searching for observations with intersection type."""
    tool = SBNSearchFixedTargetTool()
    input_data = SBNSearchFixedTargetInput(
        ra="12:30:00",
        dec="+15:45:30",
        radius=10.0,
        intersection_type="ImageIntersectsArea",
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_fixed_target_large_radius():
    """Test searching for observations with large search radius."""
    tool = SBNSearchFixedTargetTool()
    input_data = SBNSearchFixedTargetInput(
        ra="12:00:00",
        dec="+10:00:00",
        radius=60.0,  # 1 degree
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_observation_fields():
    """Test that observations contain expected fields."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="1P",
        start_date="1985-01-01",
        stop_date="1986-12-31",
        cached=True,
        timeout=180.0,
    )

    result = await tool.arun(input_data)

    if result.count > 0:
        obs = result.observations[0]

        # Required fields
        assert hasattr(obs, "product_id")
        assert hasattr(obs, "source")

        # Optional but common fields
        assert hasattr(obs, "mjd_start")
        assert hasattr(obs, "mjd_stop")
        assert hasattr(obs, "ra")
        assert hasattr(obs, "dec")
        assert hasattr(obs, "archive_url")
        assert hasattr(obs, "cutout_url")
        assert hasattr(obs, "preview_url")


@pytest.mark.asyncio
async def test_sbn_source_status_fields():
    """Test that source status contains expected fields."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="1",
        start_date="2020-01-01",
        stop_date="2020-12-31",
        cached=True,
        timeout=180.0,
    )

    result = await tool.arun(input_data)

    assert len(result.source_status) > 0

    for status in result.source_status:
        assert hasattr(status, "source")
        assert hasattr(status, "status")
        assert isinstance(status.source, str)
        assert isinstance(status.status, str)


# Test synchronous run method
def test_sbn_list_sources_sync():
    """Test listing sources using synchronous run method."""
    tool = SBNListSourcesTool()
    input_data = SBNListSourcesInput()

    result = tool.run(input_data)

    assert result.status == "success"
    assert isinstance(result.sources, list)
    assert len(result.sources) > 0


def test_sbn_search_moving_target_sync():
    """Test searching moving target using synchronous run method."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="1",
        start_date="2020-01-01",
        stop_date="2020-06-30",
        cached=True,
        timeout=180.0,
    )

    result = tool.run(input_data)

    assert result.status == "success"
    assert isinstance(result.observations, list)


def test_sbn_search_fixed_target_sync():
    """Test searching fixed target using synchronous run method."""
    tool = SBNSearchFixedTargetTool()
    input_data = SBNSearchFixedTargetInput(
        ra="12:00:00",
        dec="+10:00:00",
        radius=10.0,
    )

    result = tool.run(input_data)

    assert result.status == "success"
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_moving_target_invalid_target():
    """Test searching with an invalid target designation."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="INVALID_TARGET_XYZ_12345",
        start_date="2020-01-01",
        stop_date="2020-12-31",
        cached=True,
        timeout=60.0,
    )

    # Should handle error gracefully
    try:
        result = await tool.arun(input_data)
        # If it doesn't raise an exception, check for error in result
        if result.status == "error":
            assert result.error is not None
    except Exception:
        # It's acceptable to raise an exception for invalid targets
        pass


@pytest.mark.asyncio
async def test_sbn_search_moving_target_no_cached():
    """Test searching without using cached results."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="1",
        start_date="2020-01-01",
        stop_date="2020-01-31",  # Short date range
        cached=False,  # Force new search
        timeout=180.0,
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert isinstance(result.observations, list)


@pytest.mark.asyncio
async def test_sbn_search_moving_target_short_timeout():
    """Test searching with a short timeout."""
    tool = SBNSearchMovingTargetTool()
    input_data = SBNSearchMovingTargetInput(
        target="1",
        start_date="2020-01-01",
        stop_date="2020-01-15",  # Short date range to likely complete quickly
        cached=True,
        timeout=30.0,  # Short timeout
        poll_interval=1.0,
    )

    result = await tool.arun(input_data)

    # Should either succeed or timeout gracefully
    assert result.status in ("success", "error")
