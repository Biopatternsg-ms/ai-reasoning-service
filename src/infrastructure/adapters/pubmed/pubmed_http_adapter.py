import httpx
import logging
from typing import Optional
from src.domain.ports.pubmed_port import PubMedDataPort
from src.domain.models.pre_alignment import PipelinePreAlignmentData
from src.infrastructure.config.settings import settings
from src.infrastructure.adapters.pubmed.dtos.pubmed_response_dto import AlignedResultPubMedDTO

logger = logging.getLogger(__name__)


class PubMedHttpAdapter(PubMedDataPort):
    """
    Driven adapter implementing PubMedDataPort by querying the
    pubmed-integration Quarkus microservice via HTTP.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or settings.pubmed_integration_url).rstrip("/")
        self.timeout = timeout or settings.pubmed_timeout_seconds

    async def get_aligned_results(self, pipeline_id: str, user_id: str) -> PipelinePreAlignmentData:
        """
        Queries preliminary alignment results from pubmed-integration:
        GET /pubmed/aligned-results/{pipelineId}
        Forwarding the mandatory 'x-user-id' header.
        """
        url = f"{self.base_url}/pubmed/aligned-results/{pipeline_id}"
        logger.info(f"Querying pubmed-integration at: {url} with x-user-id: {user_id}")

        headers = {"x-user-id": user_id}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                dto = AlignedResultPubMedDTO.model_validate(data)
                return dto.to_domain()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} querying pubmed-integration: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Connection error with pubmed-integration ({url}): {str(e)}")
                raise
