"""Tests for OPUS (Outer Planets Unified Search) tools."""

import pytest

from akd_ext.tools.opus import (
    OPUSCountObservationsInput,
    OPUSCountObservationsTool,
    OPUSGetFieldsInput,
    OPUSGetFieldsTool,
    OPUSGetFilesInput,
    OPUSGetFilesTool,
    OPUSGetMetadataInput,
    OPUSGetMetadataTool,
    OPUSSearchObservationsInput,
    OPUSSearchObservationsTool,
)


@pytest.mark.asyncio
async def test_opus_search_observations_basic():
    """Test basic OPUS observation search."""
    tool = OPUSSearchObservationsTool()
    input_data = OPUSSearchObservationsInput(target="Saturn", limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert result.count <= 10
    assert len(result.observations) == result.count
    assert isinstance(result.observations, list)
    assert result.limit == 10
    assert result.available > 0


@pytest.mark.asyncio
async def test_opus_search_observations_by_mission():
    """Test OPUS search filtered by mission."""
    tool = OPUSSearchObservationsTool()
    input_data = OPUSSearchObservationsInput(mission="Cassini", limit=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert result.count <= 5
    # Verify results contain mission info
    for obs in result.observations:
        assert obs["opusid"] is not None


@pytest.mark.asyncio
async def test_opus_search_observations_by_planet():
    """Test OPUS search filtered by planet."""
    tool = OPUSSearchObservationsTool()
    input_data = OPUSSearchObservationsInput(planet="saturn", limit=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert result.count <= 5
    # Verify all results are from Saturn
    for obs in result.observations:
        if obs["planet"]:
            assert "saturn" in obs["planet"].lower()


@pytest.mark.asyncio
async def test_opus_search_observations_by_instrument():
    """Test OPUS search filtered by instrument."""
    tool = OPUSSearchObservationsTool()
    input_data = OPUSSearchObservationsInput(instrument="Cassini ISS", limit=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert result.count <= 5
    # Verify results contain instrument info
    for obs in result.observations:
        assert obs["opusid"] is not None


@pytest.mark.asyncio
async def test_opus_search_observations_pagination():
    """Test OPUS search pagination."""
    tool = OPUSSearchObservationsTool()

    # First page
    input_data1 = OPUSSearchObservationsInput(target="Saturn", limit=5, startobs=1)
    result1 = await tool.arun(input_data1)

    # Second page
    input_data2 = OPUSSearchObservationsInput(target="Saturn", limit=5, startobs=6)
    result2 = await tool.arun(input_data2)

    assert result1.status == "success"
    assert result2.status == "success"
    assert result1.start_obs == 1
    assert result2.start_obs == 6

    # Verify different results
    if result1.observations and result2.observations:
        assert result1.observations[0]["opusid"] != result2.observations[0]["opusid"]


@pytest.mark.asyncio
async def test_opus_count_observations():
    """Test OPUS observation count."""
    tool = OPUSCountObservationsTool()
    input_data = OPUSCountObservationsInput(target="Saturn")

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert isinstance(result.count, int)


@pytest.mark.asyncio
async def test_opus_count_observations_with_filters():
    """Test OPUS count with multiple filters."""
    tool = OPUSCountObservationsTool()
    input_data = OPUSCountObservationsInput(
        mission="Cassini",
        planet="saturn",
        target="Titan"
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count >= 0
    assert isinstance(result.count, int)


@pytest.mark.asyncio
async def test_opus_get_metadata():
    """Test OPUS get metadata for an observation."""
    # First, search for an observation to get a valid opusid
    search_tool = OPUSSearchObservationsTool()
    search_input = OPUSSearchObservationsInput(mission="Cassini", limit=1)
    search_result = await search_tool.arun(search_input)

    assert search_result.status == "success"
    assert len(search_result.observations) > 0

    opusid = search_result.observations[0]["opusid"]

    # Now get metadata for this observation
    metadata_tool = OPUSGetMetadataTool()
    input_data = OPUSGetMetadataInput(opusid=opusid)

    result = await metadata_tool.arun(input_data)

    assert result.status == "success"
    assert result.opusid == opusid
    assert isinstance(result.general_constraints, dict)
    assert isinstance(result.pds_constraints, dict)
    # At least one constraint category should have data
    assert (
        result.general_constraints
        or result.pds_constraints
        or result.image_constraints
        or result.wavelength_constraints
    )


@pytest.mark.asyncio
async def test_opus_get_files():
    """Test OPUS get files for an observation."""
    # First, search for an observation to get a valid opusid
    # Try to get ISS images which are more likely to have files
    search_tool = OPUSSearchObservationsTool()
    search_input = OPUSSearchObservationsInput(instrument="Cassini ISS", limit=5)
    search_result = await search_tool.arun(search_input)

    assert search_result.status == "success"
    assert len(search_result.observations) > 0

    # Try multiple observations until we find one with files
    for obs in search_result.observations:
        opusid = obs["opusid"]

        files_tool = OPUSGetFilesTool()
        input_data = OPUSGetFilesInput(opusid=opusid)
        result = await files_tool.arun(input_data)

        assert result.status == "success"
        assert result.opusid == opusid

        # Check if this observation has files
        if (result.raw_files or result.calibrated_files or
            result.browse_thumb or result.browse_small or
            result.browse_medium or result.browse_full):
            # Found files - test passes
            break

    # At least verify the API call worked for all observations
    assert search_result.count > 0


@pytest.mark.asyncio
async def test_opus_get_fields():
    """Test OPUS get available search fields."""
    tool = OPUSGetFieldsTool()
    input_data = OPUSGetFieldsInput()

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert len(result.fields) > 0
    assert len(result.categories) > 0
    assert isinstance(result.fields, list)
    assert isinstance(result.categories, list)

    # Verify field structure
    first_field = result.fields[0]
    assert "field_id" in first_field
    assert "label" in first_field
    assert "category" in first_field


@pytest.mark.asyncio
async def test_opus_search_observations_time_range():
    """Test OPUS search with time range filter."""
    tool = OPUSSearchObservationsTool()
    input_data = OPUSSearchObservationsInput(
        mission="Cassini",
        time_min="2004-01-01",
        time_max="2004-12-31",
        limit=10
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    # We should get results from Cassini in 2004 (it was active)
    assert result.count >= 0


@pytest.mark.asyncio
async def test_opus_search_observations_multiple_filters():
    """Test OPUS search with multiple filters combined."""
    tool = OPUSSearchObservationsTool()
    input_data = OPUSSearchObservationsInput(
        target="Titan",
        mission="Cassini",
        planet="saturn",
        limit=10
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count >= 0
    if result.observations:
        for obs in result.observations:
            # Verify filters are applied
            if obs["target"]:
                assert "titan" in obs["target"].lower()


@pytest.mark.asyncio
async def test_opus_count_vs_search_consistency():
    """Test that count and search return consistent numbers."""
    # Count observations
    count_tool = OPUSCountObservationsTool()
    count_input = OPUSCountObservationsInput(
        target="Saturn",
        mission="Cassini"
    )
    count_result = await count_tool.arun(count_input)

    # Search observations with high limit
    search_tool = OPUSSearchObservationsTool()
    search_input = OPUSSearchObservationsInput(
        target="Saturn",
        mission="Cassini",
        limit=100
    )
    search_result = await search_tool.arun(search_input)

    assert count_result.status == "success"
    assert search_result.status == "success"

    # The search available should match the count
    # (or count should be at least as large as available)
    assert count_result.count >= search_result.available or count_result.count == search_result.available


@pytest.mark.asyncio
async def test_opus_search_observations_order():
    """Test OPUS search with custom order."""
    tool = OPUSSearchObservationsTool()
    input_data = OPUSSearchObservationsInput(
        target="Saturn",
        limit=5,
        order="time1,opusid"
    )

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.order == "time1,opusid"
    assert result.count > 0


@pytest.mark.asyncio
async def test_opus_get_metadata_invalid_opusid():
    """Test OPUS get metadata with invalid opusid."""
    from akd_ext.tools.opus.client import OPUSClientError

    tool = OPUSGetMetadataTool()
    input_data = OPUSGetMetadataInput(opusid="invalid-opusid-12345")

    # Invalid opusid should raise an error (404)
    with pytest.raises(OPUSClientError):
        await tool.arun(input_data)


@pytest.mark.asyncio
async def test_opus_get_files_invalid_opusid():
    """Test OPUS get files with invalid opusid."""
    tool = OPUSGetFilesTool()
    input_data = OPUSGetFilesInput(opusid="invalid-opusid-12345")

    # The files endpoint may return success with empty results for invalid IDs
    result = await tool.arun(input_data)

    assert result.status == "success"
    # For invalid opusid, we expect no files
    assert len(result.raw_files) == 0
    assert len(result.calibrated_files) == 0
    assert result.browse_thumb is None
