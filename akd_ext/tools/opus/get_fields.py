"""OPUS get fields tool for listing available search fields and their definitions."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.opus.client import OPUSClient


class OPUSGetFieldsInput(InputSchema):
    """Input schema for OPUS get fields tool."""

    pass  # No input parameters needed


class OPUSFieldDefinition(OutputSchema):
    """OPUS field definition."""

    field_id: str = Field(..., description="Field identifier")
    label: str = Field(..., description="Human-readable label")
    category: str = Field(..., description="Field category")
    search_label: str | None = Field(default=None, description="Label used in search interface")
    full_label: str | None = Field(default=None, description="Full descriptive label")


class OPUSGetFieldsOutput(OutputSchema):
    """Output schema for OPUS get fields tool."""

    status: str = Field(..., description="Response status (success or error)")
    fields: list[OPUSFieldDefinition] = Field(default_factory=list, description="List of available search fields")
    categories: list[str] = Field(default_factory=list, description="List of field categories")
    error: str | None = Field(default=None, description="Error message if status is error")


@mcp_tool
class OPUSGetFieldsTool(BaseTool[OPUSGetFieldsInput, OPUSGetFieldsOutput]):
    """Get all available search fields and their definitions.

    Retrieves a comprehensive list of all searchable fields in OPUS, including
    field IDs, labels, categories, and descriptions. Useful for discovering
    what search parameters are available.
    """

    input_schema = OPUSGetFieldsInput
    output_schema = OPUSGetFieldsOutput

    async def _arun(self, params: OPUSGetFieldsInput) -> OPUSGetFieldsOutput:
        """Execute OPUS get fields."""
        async with OPUSClient() as client:
            response = await client.get_fields()

            if response.status == "error":
                return OPUSGetFieldsOutput(
                    status=response.status,
                    error=response.error,
                )

            fields = []
            for field in response.fields:
                fields.append(
                    OPUSFieldDefinition(
                        field_id=field.field_id,
                        label=field.label,
                        category=field.category,
                        search_label=field.search_label,
                        full_label=field.full_label,
                    )
                )

            return OPUSGetFieldsOutput(
                status=response.status,
                fields=fields,
                categories=response.categories,
                error=response.error,
            )
