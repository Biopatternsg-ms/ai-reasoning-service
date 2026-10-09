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
        logger.info(f"[OUTBOUND HTTP] Calling pubmed-integration at URL: {url} with x-user-id: {user_id}")

        headers = {"x-user-id": user_id}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
                logger.info(f"[OUTBOUND HTTP] pubmed-integration responded with status {response.status_code} for URL: {url}")
                response.raise_for_status()
                data = response.json()
                dto = AlignedResultPubMedDTO.model_validate(data)
                return dto.to_domain()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} querying pubmed-integration ({url}): {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Connection error with pubmed-integration ({url}): {str(e)}")
                raise

    async def get_kb_events_by_term(self, pipeline_id: str, term: str, user_id: str) -> list:
        """
        Queries knowledge base events involving the term from pubmed-integration:
        GET /pubmed/kb-events/{pipelineId}/by-term/{term}
        """
        import urllib.parse
        encoded_term = urllib.parse.quote(term.strip())
        url = f"{self.base_url}/pubmed/kb-events/{pipeline_id}/by-term/{encoded_term}"
        logger.info(f"[OUTBOUND HTTP] Calling pubmed-integration (kb-events) at URL: {url}")

        headers = {"x-user-id": user_id}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers)
                logger.info(f"[OUTBOUND HTTP] pubmed-integration (kb-events) responded with status {response.status_code} for URL: {url}")
                if response.status_code == 404:
                    return []
                response.raise_for_status()
                data = response.json()
                from src.domain.models.evidence import KbEventDomain
                from src.infrastructure.adapters.pubmed.dtos.pubmed_response_dto import KbEventResponseDTO
                events = [KbEventResponseDTO.model_validate(item) for item in data]
                return [
                    KbEventDomain(
                        first=e.first,
                        relation=e.relation,
                        second=e.second,
                        pubmed_ids=e.pubmed_ids
                    )
                    for e in events
                ]
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} querying kb-events for '{term}': {e.response.text}")
                return []
            except Exception as e:
                logger.warning(f"Failed to fetch kb-events for term '{term}': {str(e)}")
                return []

    async def get_publications_by_pmids(self, pmids: list, user_id: str) -> list:
        """
        Queries publication abstracts for a list of PMIDs from pubmed-integration:
        POST /pubmed/publications/by-pmids
        """
        if not pmids:
            return []

        url = f"{self.base_url}/pubmed/publications/by-pmids"
        logger.info(f"[OUTBOUND HTTP] Calling pubmed-integration (publications) at URL: {url} (count: {len(pmids)})")

        headers = {"x-user-id": user_id}
        payload = {"pmids": pmids}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                logger.info(f"[OUTBOUND HTTP] pubmed-integration (publications) responded with status {response.status_code} for URL: {url}")
                response.raise_for_status()
                data = response.json()
                from src.domain.models.evidence import PublicationEvidence
                from src.infrastructure.adapters.pubmed.dtos.pubmed_response_dto import PublicationResponseDTO
                pubs = [PublicationResponseDTO.model_validate(item) for item in data]
                return [
                    PublicationEvidence(
                        pmid=p.pmid,
                        title=p.title,
                        text=p.text
                    )
                    for p in pubs
                ]
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} querying publications: {e.response.text}")
                return []
            except Exception as e:
                logger.warning(f"Failed to fetch publications by pmids: {str(e)}")
                return []
