from abc import ABC, abstractmethod
from typing import List
from src.domain.models.pre_alignment import PipelinePreAlignmentData
from src.domain.models.evidence import KbEventDomain, PublicationEvidence


class PubMedDataPort(ABC):
    """
    Driven / Outbound port for fetching preliminary biomedical alignment results,
    knowledge base events, and scientific publication literature from pubmed-integration.
    """

    @abstractmethod
    async def get_aligned_results(self, pipeline_id: str, user_id: str) -> PipelinePreAlignmentData:
        """
        Retrieves pre-classified entity results from pubmed-integration.
        
        :param pipeline_id: The ID of the pipeline to query.
        :param user_id: The authenticated user ID to forward.
        :return: PipelinePreAlignmentData domain object.
        """
        pass

    @abstractmethod
    async def get_kb_events_by_term(self, pipeline_id: str, term: str, user_id: str) -> List[KbEventDomain]:
        """
        Retrieves knowledge base interaction events where the specified biological term appears.
        
        :param pipeline_id: The ID of the pipeline to query.
        :param term: Biological entity symbol to search.
        :param user_id: Authenticated user ID.
        :return: List of KbEventDomain objects.
        """
        pass

    @abstractmethod
    async def get_publications_by_pmids(self, pmids: List[str], user_id: str) -> List[PublicationEvidence]:
        """
        Retrieves publication title and abstract text for a batch of PubMed IDs.
        
        :param pmids: List of PubMed IDs.
        :param user_id: Authenticated user ID.
        :return: List of PublicationEvidence objects.
        """
        pass
