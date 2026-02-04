"""Tests for PDS4 tools."""

import pytest

from akd_ext.tools.pds4 import (
    PDS4SearchBundlesInput,
    PDS4SearchBundlesTool,
    PDS4SearchCollectionsInput,
    PDS4SearchCollectionsTool,
    PDS4SearchInstrumentHostsInput,
    PDS4SearchInstrumentHostsTool,
    PDS4SearchInstrumentsInput,
    PDS4SearchInstrumentsTool,
    PDS4SearchInvestigationsInput,
    PDS4SearchInvestigationsTool,
    PDS4SearchTargetsInput,
    PDS4SearchTargetsTool,
)


@pytest.mark.asyncio
async def test_pds4_search_investigations():
    """Test PDS4 search investigations tool."""
    tool = PDS4SearchInvestigationsTool()
    input_data = PDS4SearchInvestigationsInput(keywords="mars", limit=5)

    result = await tool.arun(input_data)

    assert result.total_hits >= 0
    assert result.limit == 5
    assert isinstance(result.investigations, list)


@pytest.mark.asyncio
async def test_pds4_search_targets():
    """Test PDS4 search targets tool."""
    tool = PDS4SearchTargetsTool()
    input_data = PDS4SearchTargetsInput(keywords="jupiter", target_type="Planet", limit=5)

    result = await tool.arun(input_data)

    assert result.total_hits >= 0
    assert result.limit == 5
    assert isinstance(result.targets, list)


@pytest.mark.asyncio
async def test_pds4_search_instruments():
    """Test PDS4 search instruments tool."""
    tool = PDS4SearchInstrumentsTool()
    input_data = PDS4SearchInstrumentsInput(keywords="camera", limit=5)

    result = await tool.arun(input_data)

    assert result.total_hits >= 0
    assert result.limit == 5
    assert isinstance(result.instruments, list)


@pytest.mark.asyncio
async def test_pds4_search_instrument_hosts():
    """Test PDS4 search instrument hosts tool."""
    tool = PDS4SearchInstrumentHostsTool()
    input_data = PDS4SearchInstrumentHostsInput(keywords="cassini", limit=5)

    result = await tool.arun(input_data)

    assert result.total_hits >= 0
    assert result.limit == 5
    assert isinstance(result.instrument_hosts, list)


@pytest.mark.asyncio
async def test_pds4_search_collections():
    """Test PDS4 search collections tool."""
    tool = PDS4SearchCollectionsTool()
    input_data = PDS4SearchCollectionsInput(
        ref_lid_target="urn:nasa:pds:context:target:planet.mars",
        limit=5,
    )

    result = await tool.arun(input_data)

    assert result.total_hits >= 0
    assert result.limit == 5
    assert isinstance(result.collections, list)


@pytest.mark.asyncio
async def test_pds4_search_bundles():
    """Test PDS4 search bundles tool."""
    tool = PDS4SearchBundlesTool()
    input_data = PDS4SearchBundlesInput(title_query="Mars", limit=5)

    result = await tool.arun(input_data)

    assert result.total_hits >= 0
    assert result.limit == 5
    assert isinstance(result.bundles, list)
    assert isinstance(result.facets, dict)


@pytest.mark.asyncio
async def test_pds4_search_investigations_no_keywords():
    """Test PDS4 search investigations without keywords."""
    tool = PDS4SearchInvestigationsTool()
    input_data = PDS4SearchInvestigationsInput(limit=3)

    result = await tool.arun(input_data)

    assert result.total_hits >= 0
    assert result.limit == 3
    assert isinstance(result.investigations, list)


@pytest.mark.asyncio
async def test_pds4_search_targets_with_type():
    """Test PDS4 search targets with type filter."""
    tool = PDS4SearchTargetsTool()
    input_data = PDS4SearchTargetsInput(target_type="Satellite", limit=5)

    result = await tool.arun(input_data)

    assert result.total_hits >= 0
    assert result.limit == 5
    assert isinstance(result.targets, list)
