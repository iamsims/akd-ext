"""OPUS (Outer Planets Unified Search) tools for planetary science data access."""

from akd_ext.tools.opus.client import OPUSClient, OPUSClientError, OPUSRateLimitError
from akd_ext.tools.opus.count_observations import (
    OPUSCountObservationsInput,
    OPUSCountObservationsOutput,
    OPUSCountObservationsTool,
)
from akd_ext.tools.opus.get_fields import OPUSGetFieldsInput, OPUSGetFieldsOutput, OPUSGetFieldsTool
from akd_ext.tools.opus.get_files import OPUSGetFilesInput, OPUSGetFilesOutput, OPUSGetFilesTool
from akd_ext.tools.opus.get_metadata import OPUSGetMetadataInput, OPUSGetMetadataOutput, OPUSGetMetadataTool
from akd_ext.tools.opus.models import (
    OPUSCountResponse,
    OPUSField,
    OPUSFieldsResponse,
    OPUSFileInfo,
    OPUSFiles,
    OPUSFilesResponse,
    OPUSMetadata,
    OPUSMetadataResponse,
    OPUSObservation,
    OPUSSearchResponse,
)
from akd_ext.tools.opus.search_observations import (
    OPUSSearchObservationsInput,
    OPUSSearchObservationsOutput,
    OPUSSearchObservationsTool,
)

__all__ = [
    # Client
    "OPUSClient",
    "OPUSClientError",
    "OPUSRateLimitError",
    # Models
    "OPUSObservation",
    "OPUSSearchResponse",
    "OPUSCountResponse",
    "OPUSMetadata",
    "OPUSMetadataResponse",
    "OPUSFileInfo",
    "OPUSFiles",
    "OPUSFilesResponse",
    "OPUSField",
    "OPUSFieldsResponse",
    # Search observations tool
    "OPUSSearchObservationsTool",
    "OPUSSearchObservationsInput",
    "OPUSSearchObservationsOutput",
    # Count observations tool
    "OPUSCountObservationsTool",
    "OPUSCountObservationsInput",
    "OPUSCountObservationsOutput",
    # Get metadata tool
    "OPUSGetMetadataTool",
    "OPUSGetMetadataInput",
    "OPUSGetMetadataOutput",
    # Get files tool
    "OPUSGetFilesTool",
    "OPUSGetFilesInput",
    "OPUSGetFilesOutput",
    # Get fields tool
    "OPUSGetFieldsTool",
    "OPUSGetFieldsInput",
    "OPUSGetFieldsOutput",
]
