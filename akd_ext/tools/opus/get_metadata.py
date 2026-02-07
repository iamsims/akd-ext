"""OPUS get metadata tool for retrieving detailed observation metadata."""

from typing import Any

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.opus.client import OPUSClient


class OPUSGetMetadataInput(InputSchema):
    """Input schema for OPUS get metadata tool."""

    opusid: str = Field(..., description="OPUS observation ID (e.g., 'co-iss-n1460960653')")


class OPUSGetMetadataOutput(OutputSchema):
    """Output schema for OPUS get metadata tool."""

    status: str = Field(..., description="Response status (success or error)")
    opusid: str | None = Field(default=None, description="OPUS observation ID")
    general_constraints: dict[str, Any] = Field(default_factory=dict, description="General observation constraints")
    pds_constraints: dict[str, Any] = Field(default_factory=dict, description="PDS-specific constraints")
    image_constraints: dict[str, Any] = Field(default_factory=dict, description="Image-specific constraints")
    wavelength_constraints: dict[str, Any] = Field(default_factory=dict, description="Wavelength constraints")
    ring_geometry_constraints: dict[str, Any] = Field(default_factory=dict, description="Ring geometry constraints")
    surface_geometry_constraints: dict[str, Any] = Field(default_factory=dict, description="Surface geometry constraints")
    instrument_constraints: dict[str, Any] = Field(default_factory=dict, description="Instrument-specific constraints")
    error: str | None = Field(default=None, description="Error message if status is error")


@mcp_tool
class OPUSGetMetadataTool(BaseTool[OPUSGetMetadataInput, OPUSGetMetadataOutput]):
    """Get detailed metadata for a specific OPUS observation.

    Retrieves comprehensive metadata including general constraints, PDS information,
    image properties, wavelength data, geometry constraints, and instrument-specific
    parameters for a given observation ID.
    """

    input_schema = OPUSGetMetadataInput
    output_schema = OPUSGetMetadataOutput

    async def _arun(self, params: OPUSGetMetadataInput) -> OPUSGetMetadataOutput:
        """Execute OPUS get metadata."""
        async with OPUSClient() as client:
            response = await client.get_metadata(opusid=params.opusid)

            if response.status == "error" or response.metadata is None:
                return OPUSGetMetadataOutput(
                    status=response.status,
                    error=response.error,
                )

            metadata = response.metadata
            return OPUSGetMetadataOutput(
                status=response.status,
                opusid=metadata.opusid,
                general_constraints=metadata.general_constraints,
                pds_constraints=metadata.pds_constraints,
                image_constraints=metadata.image_constraints,
                wavelength_constraints=metadata.wavelength_constraints,
                ring_geometry_constraints=metadata.ring_geometry_constraints,
                surface_geometry_constraints=metadata.surface_geometry_constraints,
                instrument_constraints=metadata.instrument_constraints,
                error=response.error,
            )
