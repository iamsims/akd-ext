"""Pydantic models for PDS4 API responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PDS4Summary(BaseModel):
    """PDS4 search response summary."""

    hits: int
    took: int | None = None
    q: str | None = None
    start: int = 0
    properties: list[Any] = Field(default_factory=list)
    facets: list[dict[str, Any]] = Field(default_factory=list)


class PDS4Facet(BaseModel):
    """PDS4 facet information."""

    property: str
    type: str
    counts: dict[str, int]


class PDS4IdentificationArea(BaseModel):
    """PDS4 Identification Area properties."""

    title: str | None = Field(None, alias="pds:Identification_Area.pds:title")
    logical_identifier: str | None = Field(None, alias="pds:Identification_Area.pds:logical_identifier")
    version_id: str | None = Field(None, alias="pds:Identification_Area.pds:version_id")
    product_class: str | None = Field(None, alias="pds:Identification_Area.pds:product_class")

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> "PDS4IdentificationArea":
        """Create from PDS4 properties dict where values are arrays."""

        def get_first_value(key: str) -> str | None:
            values = properties.get(key, [])
            return values[0] if values else None

        return cls(
            title=get_first_value("pds:Identification_Area.pds:title"),
            logical_identifier=get_first_value("pds:Identification_Area.pds:logical_identifier"),
            version_id=get_first_value("pds:Identification_Area.pds:version_id"),
            product_class=get_first_value("pds:Identification_Area.pds:product_class"),
        )


class PDS4InvestigationArea(BaseModel):
    """PDS4 Investigation Area properties."""

    name: str | None = Field(None, alias="pds:Investigation_Area.pds:name")
    type: str | None = Field(None, alias="pds:Investigation_Area.pds:type")
    title: str | None = Field(None, alias="pds:Investigation_Area.pds:title")

    @classmethod
    def from_properties(cls, properties: dict[str, Any]) -> "PDS4InvestigationArea":
        """Create from PDS4 properties dict where values are arrays."""

        def get_first_value(key: str) -> str | None:
            values = properties.get(key, [])
            return values[0] if values else None

        return cls(
            name=get_first_value("pds:Investigation_Area.pds:name"),
            type=get_first_value("pds:Investigation_Area.pds:type"),
            title=get_first_value("pds:Investigation_Area.pds:title"),
        )


class PDS4TargetIdentification(BaseModel):
    """PDS4 Target Identification properties."""

    name: str | None = Field(None, alias="pds:Target_Identification.pds:name")
    type: str | None = Field(None, alias="pds:Target_Identification.pds:type")


class PDS4TimeCoordinates(BaseModel):
    """PDS4 Time Coordinates properties."""

    start_date_time: datetime | None = Field(None, alias="pds:Time_Coordinates.pds:start_date_time")
    stop_date_time: datetime | None = Field(None, alias="pds:Time_Coordinates.pds:stop_date_time")


class PDS4HarvestInfo(BaseModel):
    """PDS4 Harvest Information properties."""

    node_name: str | None = Field(None, alias="ops:Harvest_Info.ops:node_name")
    harvest_date_time: datetime | None = Field(None, alias="ops:Harvest_Info.ops:harvest_date_time")


class PDS4Investigation(BaseModel):
    """PDS4 Investigation properties."""

    start_date: str | None = Field(None, alias="pds:Investigation.pds:start_date")
    stop_date: str | None = Field(None, alias="pds:Investigation.pds:stop_date")
    type: str | None = Field(None, alias="pds:Investigation.pds:type")


class PDS4Target(BaseModel):
    """PDS4 Target properties."""

    type: str | None = Field(None, alias="pds:Target.pds:type")
    description: str | None = Field(None, alias="pds:Target.pds:description")


class PDS4Instrument(BaseModel):
    """PDS4 Instrument properties."""

    type: str | None = Field(None, alias="pds:Instrument.pds:type")
    description: str | None = Field(None, alias="pds:Instrument.pds:description")


class PDS4InstrumentHost(BaseModel):
    """PDS4 Instrument Host properties."""

    type: str | None = Field(None, alias="pds:Instrument_Host.pds:type")
    description: str | None = Field(None, alias="pds:Instrument_Host.pds:description")


class PDS4Alias(BaseModel):
    """PDS4 Alias properties."""

    alternate_title: str | None = Field(None, alias="pds:Alias.pds:alternate_title")


class PDS4LabelFileInfo(BaseModel):
    """PDS4 Label File Info properties."""

    file_ref: str | None = Field(None, alias="ops:Label_File_Info.ops:file_ref")


class PDS4Product(BaseModel):
    """PDS4 Product representation with structured properties."""

    id: str
    lid: str | None = None
    lidvid: str | None = None
    title: str | None = None

    identification_area: PDS4IdentificationArea | None = None
    investigation_area: PDS4InvestigationArea | None = None
    target_identification: PDS4TargetIdentification | None = None
    time_coordinates: PDS4TimeCoordinates | None = None
    harvest_info: PDS4HarvestInfo | None = None

    investigation: PDS4Investigation | None = None
    target: PDS4Target | None = None
    instrument: PDS4Instrument | None = None
    instrument_host: PDS4InstrumentHost | None = None
    alias: PDS4Alias | None = None
    label_file_info: PDS4LabelFileInfo | None = None

    ref_lid_instrument: str | None = None
    ref_lid_target: str | None = None
    ref_lid_instrument_host: str | None = None
    ref_lid_investigation: str | None = None

    properties: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_raw_data(cls, data: dict[str, Any]) -> "PDS4Product":
        """Create PDS4Product from raw API response data."""
        properties = data.get("properties", {}) if "properties" in data else data

        def get_first_value(key: str) -> str | None:
            values = properties.get(key, [])
            if isinstance(values, list):
                return values[0] if values else None
            return values

        identification_area = PDS4IdentificationArea.from_properties(properties)
        investigation_area = PDS4InvestigationArea.from_properties(properties)

        target_identification = PDS4TargetIdentification(
            name=get_first_value("pds:Target_Identification.pds:name"),
            type=get_first_value("pds:Target_Identification.pds:type"),
        )

        time_coordinates = PDS4TimeCoordinates(start_date_time=None, stop_date_time=None)

        harvest_info = PDS4HarvestInfo(
            node_name=get_first_value("ops:Harvest_Info.ops:node_name"), harvest_date_time=None
        )

        investigation = PDS4Investigation(
            start_date=get_first_value("pds:Investigation.pds:start_date"),
            stop_date=get_first_value("pds:Investigation.pds:stop_date"),
            type=get_first_value("pds:Investigation.pds:type"),
        )

        target = PDS4Target(
            type=get_first_value("pds:Target.pds:type"),
            description=get_first_value("pds:Target.pds:description"),
        )

        instrument = PDS4Instrument(
            type=get_first_value("pds:Instrument.pds:type"),
            description=get_first_value("pds:Instrument.pds:description"),
        )

        instrument_host = PDS4InstrumentHost(
            type=get_first_value("pds:Instrument_Host.pds:type"),
            description=get_first_value("pds:Instrument_Host.pds:description"),
        )

        alias = PDS4Alias(alternate_title=get_first_value("pds:Alias.pds:alternate_title"))

        label_file_info = PDS4LabelFileInfo(file_ref=get_first_value("ops:Label_File_Info.ops:file_ref"))

        return cls(
            id=data.get("id", ""),
            lid=get_first_value("lid"),
            lidvid=get_first_value("lidvid"),
            title=data.get("title")
            or get_first_value("pds:Identification_Area.pds:title")
            or get_first_value("title"),
            identification_area=(
                identification_area if any(identification_area.model_dump(exclude_none=True).values()) else None
            ),
            investigation_area=(
                investigation_area if any(investigation_area.model_dump(exclude_none=True).values()) else None
            ),
            target_identification=(
                target_identification if any(target_identification.model_dump(exclude_none=True).values()) else None
            ),
            time_coordinates=time_coordinates if any(time_coordinates.model_dump(exclude_none=True).values()) else None,
            harvest_info=harvest_info if any(harvest_info.model_dump(exclude_none=True).values()) else None,
            investigation=investigation if any(investigation.model_dump(exclude_none=True).values()) else None,
            target=target if any(target.model_dump(exclude_none=True).values()) else None,
            instrument=instrument if any(instrument.model_dump(exclude_none=True).values()) else None,
            instrument_host=instrument_host if any(instrument_host.model_dump(exclude_none=True).values()) else None,
            alias=alias if any(alias.model_dump(exclude_none=True).values()) else None,
            label_file_info=label_file_info if any(label_file_info.model_dump(exclude_none=True).values()) else None,
            ref_lid_instrument=get_first_value("ref_lid_instrument"),
            ref_lid_target=get_first_value("ref_lid_target"),
            ref_lid_instrument_host=get_first_value("ref_lid_instrument_host"),
            ref_lid_investigation=get_first_value("ref_lid_investigation"),
            properties=properties,
        )


class PDS4SearchResponse(BaseModel):
    """PDS4 search response wrapper."""

    summary: PDS4Summary
    data: list[PDS4Product] = Field(default_factory=list)
    facets: list[PDS4Facet] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    @classmethod
    def from_raw_data(cls, data: dict[str, Any]) -> "PDS4SearchResponse":
        """Create PDS4SearchResponse from raw API response data."""
        summary_data = data.get("summary", {})

        facets = []
        for facet_data in summary_data.get("facets", []):
            facets.append(PDS4Facet(**facet_data))

        summary = PDS4Summary(
            hits=summary_data.get("hits", 0),
            took=summary_data.get("took"),
            q=summary_data.get("q"),
            start=summary_data.get("start", 0),
            properties=summary_data.get("properties", []),
        )

        products = []
        for item in data.get("data", []):
            products.append(PDS4Product.from_raw_data(item))

        return cls(summary=summary, data=products, facets=facets)
