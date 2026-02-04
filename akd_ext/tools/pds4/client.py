"""PDS4 API client wrapper with httpx."""

import asyncio
import logging
from typing import Any
from urllib.parse import urljoin

import httpx
import requests
from pydantic import ValidationError

from akd_ext.tools.pds4.models import PDS4SearchResponse

logger = logging.getLogger(__name__)


class PDS4ClientError(Exception):
    """Base exception for PDS4 client errors."""

    pass


class PDS4RateLimitError(PDS4ClientError):
    """Rate limit error for PDS4 API."""

    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")


class PDS4Client:
    """Async HTTP client for NASA PDS4 Search API."""

    BASE_URL = "https://pds.mcp.nasa.gov/api/search/1/"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize PDS4 client.

        Args:
            base_url: PDS4 API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
        """
        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PDS4Client":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Accept": "application/json", "User-Agent": "akd-ext-PDS4-Client/0.1.0"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _clean_urn(self, urn: str) -> str:
        """Clean a URN by removing version information."""
        if "::" in urn:
            return urn.split("::")[0]
        return urn

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        **kwargs,
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        url = urljoin(self.base_url, endpoint)

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method=method, url=url, params=params, **kwargs)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("retry-after", self.retry_delay))
                    if attempt < self.max_retries:
                        logger.warning(f"Rate limited. Retrying in {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        raise PDS4RateLimitError(retry_after)

                response.raise_for_status()
                return response

            except httpx.HTTPError as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2**attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}). Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise PDS4ClientError(f"Request failed after {self.max_retries} retries: {e}")

        raise PDS4ClientError("Maximum retries exceeded")

    async def search_bundles(
        self,
        title_query: str | None = None,
        limit: int | None = None,
        facet_fields: list[str] | None = None,
        facet_limit: int = 25,
    ) -> PDS4SearchResponse:
        """Search for bundles in PDS4."""
        params = {}
        if title_query:
            params["q"] = f'((title like "{title_query}"))'
        if facet_fields:
            params["facet-fields"] = ",".join(facet_fields)
        params["facet-limit"] = str(facet_limit)
        params["limit"] = str(limit or 0)

        response = await self._request("GET", "classes/bundle", params=params)
        try:
            data = response.json()
            return PDS4SearchResponse.from_raw_data(data)
        except ValidationError as e:
            logger.error(f"Failed to parse bundle search response: {e}")
            raise PDS4ClientError(f"Invalid response format: {e}")

    async def search_context_investigations(
        self,
        keywords: str | None = None,
        limit: int = 10,
    ) -> PDS4SearchResponse:
        """Search PDS Context products that are Investigations."""
        params = {
            "q": r'(product_class eq "Product_Context" and lid like "urn:nasa:pds:context:investigation:*")',
            "fields": "title,lid,pds:Investigation.pds:stop_date,pds:Investigation.pds:start_date,pds:Investigation.pds:type,ops:Label_File_Info.ops:file_ref",
            "limit": str(limit),
        }

        if keywords:
            keywords_str = " ".join(keywords.split())
            keyword_query = f'((title like "{keywords_str}") or (description like "{keywords_str}"))'
            params["q"] = f'({params["q"]} and {keyword_query})'

        response = await self._request("GET", "products", params=params)
        try:
            data = response.json()
            return PDS4SearchResponse.from_raw_data(data)
        except ValidationError as e:
            logger.error(f"Failed to parse investigation search response: {e}")
            raise PDS4ClientError(f"Invalid response format: {e}")

    async def search_context_targets(
        self,
        keywords: str | None = None,
        target_type: str | None = None,
        limit: int = 10,
    ) -> PDS4SearchResponse:
        """Search PDS Context products that are Targets."""
        params = {
            "q": r'(product_class eq "Product_Context" and lid like "urn:nasa:pds:context:target:*")',
            "fields": "title,lid,pds:Target.pds:type,pds:Alias.pds:alternate_title",
            "limit": str(limit),
        }

        if keywords:
            keyword_query = f'((title like "{keywords}") or (pds:Target.pds:description like "{keywords}"))'
            params["q"] = f'({params["q"]} and {keyword_query})'

        if target_type:
            params["q"] = f'({params["q"]} and ((pds:Target.pds:type like "{target_type}")))'

        response = await self._request("GET", "products", params=params)
        try:
            data = response.json()
            return PDS4SearchResponse.from_raw_data(data)
        except ValidationError as e:
            logger.error(f"Failed to parse target search response: {e}")
            raise PDS4ClientError(f"Invalid response format: {e}")

    async def search_context_instrument_hosts(
        self,
        keywords: str | None = None,
        instrument_host_type: str | None = None,
        limit: int = 10,
    ) -> PDS4SearchResponse:
        """Search PDS Context products that are Instrument Hosts."""
        params = {
            "q": r'(product_class eq "Product_Context" and lid like "urn:nasa:pds:context:instrument_host:*")',
            "fields": "pds:Instrument_Host.pds:type",
            "limit": str(limit),
        }

        if keywords:
            keyword_query = f'((title like "{keywords}") or (pds:Instrument_Host.pds:description like "{keywords}"))'
            params["q"] = f'({params["q"]} and {keyword_query})'

        if instrument_host_type:
            params["q"] = f'({params["q"]} and ((pds:Instrument_Host.pds:type like "{instrument_host_type}")))'

        response = await self._request("GET", "products", params=params)
        try:
            data = response.json()
            return PDS4SearchResponse.from_raw_data(data)
        except ValidationError as e:
            logger.error(f"Failed to parse instrument host search response: {e}")
            raise PDS4ClientError(f"Invalid response format: {e}")

    async def search_context_instruments(
        self,
        keywords: str | None = None,
        instrument_type: str | None = None,
        limit: int = 10,
    ) -> PDS4SearchResponse:
        """Search PDS Context products that are Instruments."""
        params = {
            "q": r'(product_class eq "Product_Context" and lid like "urn:nasa:pds:context:instrument:*")',
            "fields": "pds:Instrument.pds:type",
            "limit": str(limit),
        }

        if keywords:
            keyword_query = f'((title like "{keywords}") or (pds:Instrument.pds:description like "{keywords}"))'
            params["q"] = f'({params["q"]} and {keyword_query})'

        if instrument_type:
            params["q"] = f'({params["q"]} and ((pds:Instrument.pds:type like "{instrument_type}")))'

        response = await self._request("GET", "products", params=params)
        try:
            data = response.json()
            return PDS4SearchResponse.from_raw_data(data)
        except ValidationError as e:
            logger.error(f"Failed to parse instrument search response: {e}")
            raise PDS4ClientError(f"Invalid response format: {e}")

    async def search_context_collections(
        self,
        ref_lid_instrument: str | None = None,
        ref_lid_target: str | None = None,
        ref_lid_instrument_host: str | None = None,
        ref_lid_investigation: str | None = None,
        limit: int = 10,
    ) -> PDS4SearchResponse:
        """Search PDS data collections filtered by context references."""
        params = {
            "q": r'(product_class eq "Product_Collection")',
            "fields": "title,lid,ref_lid_instrument,ref_lid_target,ref_lid_instrument_host,ref_lid_investigation,ops:Label_File_Info.ops:file_ref",
            "limit": str(limit),
        }

        filters = []
        if ref_lid_instrument:
            filters.append(f'(ref_lid_instrument eq "{self._clean_urn(ref_lid_instrument)}")')
        if ref_lid_target:
            filters.append(f'(ref_lid_target eq "{self._clean_urn(ref_lid_target)}")')
        if ref_lid_instrument_host:
            filters.append(f'(ref_lid_instrument_host eq "{self._clean_urn(ref_lid_instrument_host)}")')
        if ref_lid_investigation:
            filters.append(f'(ref_lid_investigation eq "{self._clean_urn(ref_lid_investigation)}")')

        if filters:
            params["q"] = f'({params["q"]} and {" and ".join(filters)})'

        response = await self._request("GET", "products", params=params)
        try:
            data = response.json()
            return PDS4SearchResponse.from_raw_data(data)
        except ValidationError as e:
            logger.error(f"Failed to parse collection search response: {e}")
            raise PDS4ClientError(f"Invalid response format: {e}")

    async def get_product(self, urn: str) -> dict[str, Any]:
        """Get a single PDS product by its URN identifier."""
        clean_urn_id = self._clean_urn(urn)
        response = await self._request("GET", f"products/{clean_urn_id}")
        try:
            return response.json()
        except Exception as e:
            logger.error(f"Failed to parse product response: {e}")
            raise PDS4ClientError(f"Invalid response format: {e}")

    async def crawl_context_product(self, urn: str) -> dict[str, Any]:
        """Crawl a single PDS Context product and return associated context products."""
        clean_urn_id = self._clean_urn(urn)
        product_response = await self._request("GET", f"products/{clean_urn_id}")
        response_data = product_response.json()

        response_data = {
            k: v
            for k, v in response_data.items()
            if k in ("investigations", "observing_system_components", "targets", "title", "id")
        }

        urn_dict = {"investigations": {}, "observing_system_components": {}, "targets": {}}

        if "investigations" in response_data:
            for item in response_data["investigations"]:
                urn_dict["investigations"][item["id"]] = item["href"]
        if "observing_system_components" in response_data:
            for item in response_data["observing_system_components"]:
                urn_dict["observing_system_components"][item["id"]] = item["href"]
        if "targets" in response_data:
            for item in response_data["targets"]:
                urn_dict["targets"][item["id"]] = item["href"]

        results = {"investigations": {}, "observing_system_components": {}, "targets": {}}

        for category in urn_dict:
            for urn_id, href in urn_dict[category].items():
                try:
                    resp = requests.get(href, headers={"Accept": "application/kvp+json"})
                    if resp.status_code == 200:
                        data = resp.json()
                        subset_keys = ["title", "description", "id"]
                        results[category][urn_id] = {k: v for k, v in data.items() if k in subset_keys}
                except Exception as e:
                    logger.error(f"Error fetching {href}: {e}")

        return results
