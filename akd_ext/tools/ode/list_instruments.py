"""ODE list instruments tool for discovering available instrument/product type combinations."""

from akd._base import InputSchema, OutputSchema
from akd.tools import BaseTool
from pydantic import Field

from akd_ext.mcp import mcp_tool
from akd_ext.tools.ode.client import ODEClient


class ODEListInstrumentsInput(InputSchema):
    """Input schema for ODE list instruments tool."""

    target: str = Field(..., description="Planetary body (mars, moon, mercury, phobos, deimos, venus)")
    limit: int = Field(
        default=25, description="(Optional, default: 25) Maximum number of instrument combinations to return"
    )


class ODEListInstrumentsOutput(OutputSchema):
    """Output schema for ODE list instruments tool."""

    status: str = Field(..., description="Response status (SUCCESS or ERROR)")
    instruments: list[dict] = Field(..., description="List of instrument/product type combinations")
    error: str | None = Field(default=None, description="Error message if status is ERROR")


@mcp_tool
class ODEListInstrumentsTool(BaseTool[ODEListInstrumentsInput, ODEListInstrumentsOutput]):
    """List available instrument and product type combinations for a target body.

    This tool helps discover what data is available in the ODE by listing valid combinations
    of Instrument Host (spacecraft), Instrument, and Product Type for a given planetary target.

    Use this tool to explore what datasets are available before searching for specific products.
    """

    input_schema = ODEListInstrumentsInput
    output_schema = ODEListInstrumentsOutput

    async def _arun(self, params: ODEListInstrumentsInput) -> ODEListInstrumentsOutput:
        """Execute ODE list instruments query."""
        async with ODEClient() as client:
            response = await client.list_instruments(target=params.target)

            instruments = []
            for i, inst in enumerate(response.instruments):
                if i >= params.limit:
                    break

                instruments.append(
                    {
                        "ihid": inst.ihid,
                        "instrument_host_name": inst.instrument_host_name,
                        "iid": inst.iid,
                        "instrument_name": inst.instrument_name,
                        "pt": inst.pt,
                        "pt_name": inst.pt_name,
                        "number_products": inst.number_products,
                    }
                )

            return ODEListInstrumentsOutput(
                status=response.status,
                instruments=instruments,
                error=response.error,
            )
