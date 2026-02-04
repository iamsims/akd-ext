"""In-memory catalog index for PDS datasets."""

import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from .models import PDSDataset, load_from_jsonl

logger = logging.getLogger(__name__)

# Default catalog directory containing scraped JSONL files
DEFAULT_CATALOG_DIR = Path(__file__).parent / "scraped_data"

# Response limits
MAX_RESULTS_LIMIT = 50
DEFAULT_RESULTS_LIMIT = 20

# Field profiles for response filtering
ESSENTIAL_FIELDS = {"id", "title", "node", "browse_url"}
SUMMARY_FIELDS = ESSENTIAL_FIELDS | {"missions", "targets", "instruments", "pds_version", "type"}
FULL_FIELDS = SUMMARY_FIELDS | {
    "description",
    "instrument_hosts",
    "data_types",
    "start_date",
    "stop_date",
    "keywords",
    "processing_level",
    "label_url",
    "source_url",
}
FIELD_PROFILES: dict[str, set[str]] = {
    "essential": ESSENTIAL_FIELDS,
    "summary": SUMMARY_FIELDS,
    "full": FULL_FIELDS,
}


class CatalogIndex:
    """In-memory index for the PDS catalog."""

    _instance: "CatalogIndex | None" = None

    def __init__(self, datasets: list[PDSDataset]):
        """Initialize the catalog index.

        Args:
            datasets: List of PDSDataset objects
        """
        self.datasets = datasets
        self._by_node: dict[str, list[PDSDataset]] = {}
        self._by_mission: dict[str, list[PDSDataset]] = {}
        self._by_target: dict[str, list[PDSDataset]] = {}
        self._by_type: dict[str, list[PDSDataset]] = {}

        # Build indexes
        for ds in datasets:
            # By node
            node_key = ds.node.value
            if node_key not in self._by_node:
                self._by_node[node_key] = []
            self._by_node[node_key].append(ds)

            # By mission
            for mission in ds.missions:
                mission_lower = mission.lower()
                if mission_lower not in self._by_mission:
                    self._by_mission[mission_lower] = []
                self._by_mission[mission_lower].append(ds)

            # By target
            for target in ds.targets:
                target_lower = target.lower()
                if target_lower not in self._by_target:
                    self._by_target[target_lower] = []
                self._by_target[target_lower].append(ds)

            # By type (volume, bundle, collection)
            type_key = ds.type.value
            if type_key not in self._by_type:
                self._by_type[type_key] = []
            self._by_type[type_key].append(ds)

    @classmethod
    def get_instance(cls) -> "CatalogIndex":
        """Get or create the singleton catalog index instance."""
        if cls._instance is None:
            catalog_dir = Path(os.getenv("PDS_CATALOG_DIR", str(DEFAULT_CATALOG_DIR)))
            all_datasets: list[PDSDataset] = []

            if catalog_dir.is_dir():
                for jsonl_file in catalog_dir.glob("*_catalog.jsonl"):
                    # Skip test files
                    if "test" in jsonl_file.name:
                        continue
                    logger.info(f"Loading catalog from {jsonl_file}")
                    datasets = load_from_jsonl(jsonl_file)
                    all_datasets.extend(datasets)
            elif catalog_dir.is_file():
                # Backwards compat: single file
                logger.info(f"Loading catalog from {catalog_dir}")
                all_datasets = load_from_jsonl(catalog_dir)

            if not all_datasets:
                logger.warning(f"No catalog files found in: {catalog_dir}")
                logger.warning("The PDS catalog will be empty.")

            cls._instance = cls(all_datasets)
            logger.info(f"PDS Catalog Index initialized with {len(all_datasets)} datasets")

        return cls._instance

    def search(
        self,
        query: str | None = None,
        node: str | None = None,
        mission: str | None = None,
        target: str | None = None,
        pds_version: str | None = None,
        dataset_type: str | None = None,
        start_date: date | None = None,
        stop_date: date | None = None,
        limit: int = DEFAULT_RESULTS_LIMIT,
        offset: int = 0,
    ) -> tuple[list[PDSDataset], int]:
        """Search the catalog with filters.

        Args:
            query: Text search query
            node: Filter by PDS node
            mission: Filter by mission name
            target: Filter by target body
            pds_version: Filter by PDS version (PDS3 or PDS4)
            dataset_type: Filter by type (volume, bundle, collection)
            start_date: Filter datasets that have data on or after this date
            stop_date: Filter datasets that have data on or before this date
            limit: Maximum results to return
            offset: Skip first N results

        Returns:
            Tuple of (matching datasets, total count)
        """
        # Start with all datasets or filtered subset
        if node:
            results = self._by_node.get(node.lower(), [])
        elif mission:
            results = self._by_mission.get(mission.lower(), [])
        elif target:
            results = self._by_target.get(target.lower(), [])
        else:
            results = self.datasets

        # Apply additional filters
        if node and mission:
            results = [d for d in results if d.node.value == node.lower()]
        if node and target:
            results = [d for d in results if d.node.value == node.lower()]
        if mission and not node:
            mission_lower = mission.lower()
            results = [d for d in results if any(mission_lower in m.lower() for m in d.missions)]
        if target and not node and not mission:
            target_lower = target.lower()
            results = [d for d in results if any(target_lower in t.lower() for t in d.targets)]

        if pds_version:
            results = [d for d in results if d.pds_version.value == pds_version.upper()]

        # Filter by dataset type
        if dataset_type:
            results = [d for d in results if d.type.value == dataset_type.lower()]

        # Temporal filtering - find datasets that overlap with the requested date range
        if start_date:
            # Include datasets that end on or after the requested start date
            results = [d for d in results if d.stop_date is None or d.stop_date >= start_date]
        if stop_date:
            # Include datasets that start on or before the requested stop date
            results = [d for d in results if d.start_date is None or d.start_date <= stop_date]

        # Apply text search with fuzzy matching
        if query:
            query_lower = query.lower()
            scored_results = []
            for d in results:
                search_text = d.to_search_text()
                # Use partial ratio for substring-like matching
                # and token_set_ratio for word reordering tolerance
                score = max(
                    fuzz.partial_ratio(query_lower, search_text),
                    fuzz.token_set_ratio(query_lower, search_text),
                )
                if score >= 70:  # Threshold for relevance
                    scored_results.append((score, d))
            # Sort by score descending
            scored_results.sort(key=lambda x: x[0], reverse=True)
            results = [d for _, d in scored_results]

        total = len(results)
        paginated = results[offset : offset + limit]

        return paginated, total

    def get_stats(self) -> dict[str, Any]:
        """Get catalog statistics."""
        stats = {
            "total_datasets": len(self.datasets),
            "by_node": {k: len(v) for k, v in sorted(self._by_node.items())},
            "by_pds_version": {},
            "by_type": {k: len(v) for k, v in sorted(self._by_type.items())},
            "missions_count": len(self._by_mission),
            "targets_count": len(self._by_target),
        }

        # Count by PDS version
        for ds in self.datasets:
            version = ds.pds_version.value
            stats["by_pds_version"][version] = stats["by_pds_version"].get(version, 0) + 1

        return stats

    def list_missions(self) -> list[dict[str, Any]]:
        """List all missions with dataset counts."""
        missions = []
        for mission, datasets in sorted(self._by_mission.items()):
            missions.append(
                {
                    "name": datasets[0].missions[0] if datasets else mission,  # Use proper casing
                    "count": len(datasets),
                    "nodes": list({d.node.value for d in datasets}),
                }
            )
        return missions

    def list_targets(self) -> list[dict[str, Any]]:
        """List all targets with dataset counts."""
        targets = []
        for target, datasets in sorted(self._by_target.items()):
            targets.append(
                {
                    "name": datasets[0].targets[0] if datasets else target,  # Use proper casing
                    "count": len(datasets),
                    "nodes": list({d.node.value for d in datasets}),
                }
            )
        return targets

    def get_dataset(self, dataset_id: str) -> PDSDataset | None:
        """Get a dataset by ID.

        Args:
            dataset_id: The dataset ID to look up

        Returns:
            PDSDataset if found, None otherwise
        """
        for dataset in self.datasets:
            if dataset.id == dataset_id:
                return dataset
        return None


def filter_dataset(dataset: PDSDataset, fields: set[str]) -> dict[str, Any]:
    """Filter dataset to specified fields."""
    result: dict[str, Any] = {}

    if "id" in fields:
        result["id"] = dataset.id
    if "title" in fields:
        result["title"] = dataset.title
    if "description" in fields and dataset.description:
        result["description"] = dataset.description
    if "node" in fields:
        result["node"] = dataset.node.value
    if "pds_version" in fields:
        result["pds_version"] = dataset.pds_version.value
    if "type" in fields:
        result["type"] = dataset.type.value
    if "missions" in fields and dataset.missions:
        result["missions"] = dataset.missions
    if "targets" in fields and dataset.targets:
        result["targets"] = dataset.targets
    if "instruments" in fields and dataset.instruments:
        result["instruments"] = dataset.instruments
    if "instrument_hosts" in fields and dataset.instrument_hosts:
        result["instrument_hosts"] = dataset.instrument_hosts
    if "data_types" in fields and dataset.data_types:
        result["data_types"] = dataset.data_types
    if "start_date" in fields and dataset.start_date:
        result["start_date"] = str(dataset.start_date)
    if "stop_date" in fields and dataset.stop_date:
        result["stop_date"] = str(dataset.stop_date)
    if "browse_url" in fields:
        result["browse_url"] = dataset.browse_url
    if "label_url" in fields and dataset.label_url:
        result["label_url"] = dataset.label_url
    if "source_url" in fields:
        result["source_url"] = dataset.source_url
    if "keywords" in fields and dataset.keywords:
        result["keywords"] = dataset.keywords
    if "processing_level" in fields and dataset.processing_level:
        result["processing_level"] = dataset.processing_level

    return result
