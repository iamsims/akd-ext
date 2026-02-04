"""OPUS get files tool for retrieving downloadable file URLs for observations."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.opus.client import OPUSClient


class OPUSGetFilesInput(InputSchema):
    """Input schema for OPUS get files tool."""

    opusid: str = Field(..., description="OPUS observation ID (e.g., 'co-iss-n1460960653')")


class OPUSGetFilesOutput(OutputSchema):
    """Output schema for OPUS get files tool."""

    status: str = Field(..., description="Response status (success or error)")
    opusid: str | None = Field(default=None, description="OPUS observation ID")
    raw_files: list[str] = Field(default_factory=list, description="URLs to raw data files")
    calibrated_files: list[str] = Field(default_factory=list, description="URLs to calibrated data files")
    browse_thumb: str | None = Field(default=None, description="URL to thumbnail browse image")
    browse_small: str | None = Field(default=None, description="URL to small browse image")
    browse_medium: str | None = Field(default=None, description="URL to medium browse image")
    browse_full: str | None = Field(default=None, description="URL to full-size browse image")
    all_files: dict[str, list[str]] = Field(
        default_factory=dict, description="All available files organized by category"
    )
    error: str | None = Field(default=None, description="Error message if status is error")


@mcp_tool
class OPUSGetFilesTool(BaseTool[OPUSGetFilesInput, OPUSGetFilesOutput]):
    """Get downloadable file URLs for an OPUS observation.

    Retrieves URLs for raw data files, calibrated data files, and browse images
    at various resolutions (thumbnail, small, medium, full) for a given observation ID.
    """

    input_schema = OPUSGetFilesInput
    output_schema = OPUSGetFilesOutput

    async def _arun(self, params: OPUSGetFilesInput) -> OPUSGetFilesOutput:
        """Execute OPUS get files."""
        async with OPUSClient() as client:
            response = await client.get_files(opusid=params.opusid)

            if response.status == "error" or response.files is None:
                return OPUSGetFilesOutput(
                    status=response.status,
                    error=response.error,
                )

            files = response.files
            return OPUSGetFilesOutput(
                status=response.status,
                opusid=files.opusid,
                raw_files=files.raw_files,
                calibrated_files=files.calibrated_files,
                browse_thumb=files.browse_thumb,
                browse_small=files.browse_small,
                browse_medium=files.browse_medium,
                browse_full=files.browse_full,
                all_files=files.all_files,
                error=response.error,
            )
