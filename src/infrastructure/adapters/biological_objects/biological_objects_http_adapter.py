import logging
import urllib.parse
from typing import List
import httpx
from src.domain.models.biological_object import BiologicalObjectDomain
from src.domain.ports.biological_objects_port import BiologicalObjectsPort
from src.infrastructure.adapters.biological_objects.dtos.biological_object_dto import BiologicalObjectResponseDTO
from src.infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class BiologicalObjectsHttpAdapter(BiologicalObjectsPort):
    """
    Driven adapter implementing BiologicalObjectsPort via HTTP calls
    to search-biological-objects service (/search-by-synonym/{synonym}).
    """

    def __init__(self):
        self.base_url = settings.search_biological_objects_url.rstrip("/")
        self.timeout = settings.search_biological_objects_timeout_seconds

    async def search_by_synonym(self, synonym: str, user_id: str) -> List[BiologicalObjectDomain]:
        """
        Queries GET /search-by-synonym/{synonym} forwarding x-user-id header.
        """
        clean_synonym = synonym.strip()
        if not clean_synonym:
            return []

        encoded_synonym = urllib.parse.quote(clean_synonym, safe="")
        url = f"{self.base_url}/biological-object/search-by-synonym/{encoded_synonym}"
        headers = {"x-user-id": user_id}

        logger.info(f"[OUTBOUND HTTP] Calling search-biological-objects at URL: {url} (synonym: '{clean_synonym}')")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
                logger.info(
                    f"[OUTBOUND HTTP] search-biological-objects responded with status {response.status_code} "
                    f"for URL: {url}"
                )
                if response.status_code == 404:
                    logger.debug(f"No biological objects found for synonym '{clean_synonym}' (404).")
                    return []

                response.raise_for_status()
                data = response.json()

                if isinstance(data, list):
                    return [BiologicalObjectResponseDTO(**item).to_domain() for item in data]
                elif isinstance(data, dict):
                    return [BiologicalObjectResponseDTO(**data).to_domain()]
                else:
                    return []

            except httpx.HTTPError as e:
                logger.warning(
                    f"HTTP error querying biological objects for synonym '{clean_synonym}' "
                    f"from {url}: {str(e)}"
                )
                return []
            except Exception as e:
                logger.error(f"Unexpected error querying biological objects: {str(e)}")
                return []
