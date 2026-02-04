"""Pydantic models for PDS Catalog datasets."""

import json
import logging
from datetime import date, datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PDSNode(str, Enum):
    """PDS node identifiers."""

    ATM = "atm"  # Atmospheres
    GEO = "geo"  # Geosciences
    IMG = "img"  # Imaging
    NAIF = "naif"  # Navigation and Ancillary Information
    PPI = "ppi"  # Planetary Plasma Interactions
    RMS = "rms"  # Ring-Moon Systems
    SBN = "sbn"  # Small Bodies


class PDSVersion(str, Enum):
    """PDS archive version."""

    PDS3 = "PDS3"
    PDS4 = "PDS4"


class DatasetType(str, Enum):
    """Type of PDS dataset."""

    BUNDLE = "bundle"
    COLLECTION = "collection"
    VOLUME = "volume"


class PDSDataset(BaseModel):
    """Unified schema for PDS4 bundles and PDS3 volumes.

    This model represents a single dataset entry in the PDS catalog,
    containing all the metadata researchers need for data discovery.
    """

    # Identity
    id: str = Field(description="LIDVID for PDS4, VOLUME_ID for PDS3")
    title: str = Field(description="Human-readable title")
    description: str | None = Field(default=None, description="Abstract/description")

    # Classification
    node: PDSNode = Field(description="PDS node (atm, geo, img, naif, ppi, rms, sbn)")
    pds_version: PDSVersion = Field(description="PDS3 or PDS4")
    type: DatasetType = Field(description="bundle, collection, or volume")

    # Discovery fields (what researchers search for)
    missions: list[str] = Field(default_factory=list, description="Mission names")
    targets: list[str] = Field(default_factory=list, description="Target bodies")
    instruments: list[str] = Field(default_factory=list, description="Instrument names")
    instrument_hosts: list[str] = Field(default_factory=list, description="Spacecraft/rover names")
    data_types: list[str] = Field(default_factory=list, description="Data types (images, spectra, etc.)")

    # Temporal coverage
    start_date: date | None = Field(default=None, description="Observation start date")
    stop_date: date | None = Field(default=None, description="Observation end date")

    # Access URLs
    browse_url: str = Field(description="Link to browse data")
    download_url: str | None = Field(default=None, description="Direct download if available")
    label_url: str | None = Field(default=None, description="URL to PDS4 label XML")

    # Metadata
    source_url: str = Field(description="Where we found this dataset")
    scraped_at: datetime = Field(default_factory=datetime.utcnow, description="When we scraped it")

    # Additional metadata
    keywords: list[str] = Field(default_factory=list, description="Additional keywords for search")
    processing_level: str | None = Field(default=None, description="Data processing level")
    file_count: int | None = Field(default=None, description="Number of files in dataset")
    total_size_bytes: int | None = Field(default=None, description="Total size in bytes")

    def to_search_text(self) -> str:
        """Generate searchable text from all fields."""
        parts = [
            self.title,
            self.description or "",
            " ".join(self.missions),
            " ".join(self.targets),
            " ".join(self.instruments),
            " ".join(self.instrument_hosts),
            " ".join(self.data_types),
            " ".join(self.keywords),
        ]
        return " ".join(parts).lower()


def load_from_jsonl(input_path: Path) -> list[PDSDataset]:
    """Load datasets from JSONL format.

    Args:
        input_path: Input file path

    Returns:
        List of PDSDataset objects
    """
    datasets = []

    with open(input_path) as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                datasets.append(PDSDataset.model_validate(data))

    logger.info(f"Loaded {len(datasets)} datasets from {input_path}")
    return datasets
