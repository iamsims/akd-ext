"""Tests for PDS Catalog tools."""

import pytest

from akd_ext.tools.pds_catalog import (
    PDSCatalogGetDatasetInput,
    PDSCatalogGetDatasetTool,
    PDSCatalogGetStatsInput,
    PDSCatalogGetStatsTool,
    PDSCatalogListMissionsInput,
    PDSCatalogListMissionsTool,
    PDSCatalogListTargetsInput,
    PDSCatalogListTargetsTool,
    PDSCatalogSearchInput,
    PDSCatalogSearchTool,
)


@pytest.mark.asyncio
async def test_pds_catalog_search_basic():
    """Test basic PDS Catalog search."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(query="mars", limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total > 0
    assert result.count > 0
    assert result.count <= 10
    assert len(result.datasets) == result.count
    assert isinstance(result.datasets, list)
    assert result.limit == 10
    assert result.offset == 0


@pytest.mark.asyncio
async def test_pds_catalog_search_by_node():
    """Test PDS Catalog search filtered by node."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(node="sbn", limit=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total > 0
    assert result.count > 0
    assert result.count <= 5
    # Verify all results are from the sbn node
    for dataset in result.datasets:
        assert dataset["node"] == "sbn"


@pytest.mark.asyncio
async def test_pds_catalog_search_by_mission():
    """Test PDS Catalog search filtered by mission."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(mission="cassini", limit=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total >= 0
    assert result.count <= 5
    # Verify all results contain the mission
    for dataset in result.datasets:
        if "missions" in dataset:
            assert any("cassini" in m.lower() for m in dataset["missions"])


@pytest.mark.asyncio
async def test_pds_catalog_search_by_target():
    """Test PDS Catalog search filtered by target."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(target="saturn", limit=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total >= 0
    assert result.count <= 5
    # Verify all results contain the target
    for dataset in result.datasets:
        if "targets" in dataset:
            assert any("saturn" in t.lower() for t in dataset["targets"])


@pytest.mark.asyncio
async def test_pds_catalog_search_by_pds_version():
    """Test PDS Catalog search filtered by PDS version."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(pds_version="PDS4", limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total >= 0
    assert result.count <= 10
    # Verify all results are PDS4
    for dataset in result.datasets:
        assert dataset["pds_version"] == "PDS4"


@pytest.mark.asyncio
async def test_pds_catalog_search_by_dataset_type():
    """Test PDS Catalog search filtered by dataset type."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(dataset_type="bundle", limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total >= 0
    assert result.count <= 10
    # Verify all results are bundles
    for dataset in result.datasets:
        assert dataset["type"] == "bundle"


@pytest.mark.asyncio
async def test_pds_catalog_search_with_pagination():
    """Test PDS Catalog search with pagination."""
    tool = PDSCatalogSearchTool()

    # Get first page
    input_data1 = PDSCatalogSearchInput(query="mars", limit=5, offset=0)
    result1 = await tool.arun(input_data1)

    # Get second page
    input_data2 = PDSCatalogSearchInput(query="mars", limit=5, offset=5)
    result2 = await tool.arun(input_data2)

    assert result1.status == "success"
    assert result2.status == "success"
    assert result1.total == result2.total  # Same total count
    assert result1.offset == 0
    assert result2.offset == 5

    # Verify different results (if enough data)
    if result1.count == 5 and result2.count > 0:
        first_ids = {d["id"] for d in result1.datasets}
        second_ids = {d["id"] for d in result2.datasets}
        assert first_ids != second_ids  # Different datasets


@pytest.mark.asyncio
async def test_pds_catalog_search_field_profiles():
    """Test PDS Catalog search with different field profiles."""
    tool = PDSCatalogSearchTool()

    # Test essential fields
    input_essential = PDSCatalogSearchInput(query="mars", limit=1, fields="essential")
    result_essential = await tool.arun(input_essential)

    assert result_essential.status == "success"
    assert result_essential.fields == "essential"
    if result_essential.datasets:
        dataset = result_essential.datasets[0]
        assert "id" in dataset
        assert "title" in dataset
        assert "browse_url" in dataset

    # Test summary fields
    input_summary = PDSCatalogSearchInput(query="mars", limit=1, fields="summary")
    result_summary = await tool.arun(input_summary)

    assert result_summary.status == "success"
    assert result_summary.fields == "summary"
    if result_summary.datasets:
        dataset = result_summary.datasets[0]
        assert "id" in dataset
        assert "title" in dataset
        # Summary includes more fields than essential
        assert "node" in dataset or "pds_version" in dataset

    # Test full fields
    input_full = PDSCatalogSearchInput(query="mars", limit=1, fields="full")
    result_full = await tool.arun(input_full)

    assert result_full.status == "success"
    assert result_full.fields == "full"
    if result_full.datasets:
        dataset = result_full.datasets[0]
        assert "id" in dataset
        assert "title" in dataset
        # Full includes all fields


@pytest.mark.asyncio
async def test_pds_catalog_search_combined_filters():
    """Test PDS Catalog search with multiple combined filters."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(query="mars", node="img", pds_version="PDS4", limit=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total >= 0
    assert result.count <= 5


@pytest.mark.asyncio
async def test_pds_catalog_search_date_range():
    """Test PDS Catalog search with date range filter."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(start_date="2020-01-01", stop_date="2023-12-31", limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total >= 0
    assert result.count <= 10


@pytest.mark.asyncio
async def test_pds_catalog_get_dataset_success():
    """Test getting a specific dataset by ID."""
    # First, search for a dataset to get a valid ID
    search_tool = PDSCatalogSearchTool()
    search_input = PDSCatalogSearchInput(limit=1)
    search_result = await search_tool.arun(search_input)

    # Skip test if no datasets available
    if search_result.count == 0:
        pytest.skip("No datasets available in catalog")

    dataset_id = search_result.datasets[0]["id"]

    # Now get the specific dataset
    get_tool = PDSCatalogGetDatasetTool()
    get_input = PDSCatalogGetDatasetInput(dataset_id=dataset_id)
    get_result = await get_tool.arun(get_input)

    assert get_result.status == "success"
    assert get_result.dataset is not None
    assert get_result.dataset["id"] == dataset_id
    assert "title" in get_result.dataset
    assert get_result.error is None


@pytest.mark.asyncio
async def test_pds_catalog_get_dataset_not_found():
    """Test getting a non-existent dataset."""
    tool = PDSCatalogGetDatasetTool()
    input_data = PDSCatalogGetDatasetInput(dataset_id="nonexistent_id_12345")

    result = await tool.arun(input_data)

    assert result.status == "not_found"
    assert result.dataset is None
    assert result.error is not None
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_pds_catalog_list_missions():
    """Test listing missions."""
    tool = PDSCatalogListMissionsTool()
    input_data = PDSCatalogListMissionsInput(limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert result.count <= 10
    assert len(result.missions) == result.count
    assert isinstance(result.missions, list)

    # Verify mission structure
    if result.missions:
        mission = result.missions[0]
        assert "name" in mission
        assert "count" in mission
        assert "nodes" in mission
        assert isinstance(mission["count"], int)
        assert isinstance(mission["nodes"], list)


@pytest.mark.asyncio
async def test_pds_catalog_list_missions_by_node():
    """Test listing missions filtered by node."""
    tool = PDSCatalogListMissionsTool()
    input_data = PDSCatalogListMissionsInput(node="sbn", limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count <= 10
    # Verify all missions include the sbn node
    for mission in result.missions:
        assert "sbn" in mission["nodes"]


@pytest.mark.asyncio
async def test_pds_catalog_list_targets():
    """Test listing targets."""
    tool = PDSCatalogListTargetsTool()
    input_data = PDSCatalogListTargetsInput(limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert result.count <= 10
    assert len(result.targets) == result.count
    assert isinstance(result.targets, list)

    # Verify target structure
    if result.targets:
        target = result.targets[0]
        assert "name" in target
        assert "count" in target
        assert "nodes" in target
        assert isinstance(target["count"], int)
        assert isinstance(target["nodes"], list)


@pytest.mark.asyncio
async def test_pds_catalog_list_targets_by_node():
    """Test listing targets filtered by node."""
    tool = PDSCatalogListTargetsTool()
    input_data = PDSCatalogListTargetsInput(node="img", limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.count <= 10
    # Verify all targets include the img node
    for target in result.targets:
        assert "img" in target["nodes"]


@pytest.mark.asyncio
async def test_pds_catalog_get_stats():
    """Test getting catalog statistics."""
    tool = PDSCatalogGetStatsTool()
    input_data = PDSCatalogGetStatsInput()

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total_datasets > 0
    assert isinstance(result.by_node, dict)
    assert isinstance(result.by_pds_version, dict)
    assert isinstance(result.by_type, dict)
    assert result.missions_count > 0
    assert result.targets_count > 0

    # Verify node statistics
    expected_nodes = ["atm", "geo", "img", "naif", "ppi", "rms", "sbn"]
    for node in expected_nodes:
        if node in result.by_node:
            assert result.by_node[node] > 0

    # Verify PDS version statistics
    assert "PDS3" in result.by_pds_version or "PDS4" in result.by_pds_version

    # Verify type statistics
    assert "bundle" in result.by_type or "volume" in result.by_type or "collection" in result.by_type


@pytest.mark.asyncio
async def test_pds_catalog_search_no_results():
    """Test PDS Catalog search with query that returns no results."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(query="nonexistent_xyz_query_12345", limit=10)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total == 0
    assert result.count == 0
    assert len(result.datasets) == 0
    assert result.has_more is False


@pytest.mark.asyncio
async def test_pds_catalog_search_max_limit():
    """Test PDS Catalog search respects maximum limit."""
    tool = PDSCatalogSearchTool()
    # Try to request more than the max limit (50)
    input_data = PDSCatalogSearchInput(query="mars", limit=100)

    result = await tool.arun(input_data)

    assert result.status == "success"
    # Should be capped at 50
    assert result.limit == 50
    assert result.count <= 50


@pytest.mark.asyncio
async def test_pds_catalog_search_empty_query():
    """Test PDS Catalog search with no filters (returns all datasets)."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(limit=5)

    result = await tool.arun(input_data)

    assert result.status == "success"
    assert result.total > 0
    assert result.count > 0
    assert result.count <= 5


# Test synchronous run method
def test_pds_catalog_search_sync():
    """Test PDS Catalog search using synchronous run method."""
    tool = PDSCatalogSearchTool()
    input_data = PDSCatalogSearchInput(query="mars", limit=5)

    result = tool.run(input_data)

    assert result.status == "success"
    assert result.total > 0
    assert result.count > 0
    assert result.count <= 5


def test_pds_catalog_get_stats_sync():
    """Test PDS Catalog get stats using synchronous run method."""
    tool = PDSCatalogGetStatsTool()
    input_data = PDSCatalogGetStatsInput()

    result = tool.run(input_data)

    assert result.status == "success"
    assert result.total_datasets > 0
    assert isinstance(result.by_node, dict)


def test_pds_catalog_list_missions_sync():
    """Test PDS Catalog list missions using synchronous run method."""
    tool = PDSCatalogListMissionsTool()
    input_data = PDSCatalogListMissionsInput(limit=5)

    result = tool.run(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert len(result.missions) == result.count


def test_pds_catalog_list_targets_sync():
    """Test PDS Catalog list targets using synchronous run method."""
    tool = PDSCatalogListTargetsTool()
    input_data = PDSCatalogListTargetsInput(limit=5)

    result = tool.run(input_data)

    assert result.status == "success"
    assert result.count > 0
    assert len(result.targets) == result.count
