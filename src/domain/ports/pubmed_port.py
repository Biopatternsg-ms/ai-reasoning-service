from abc import ABC, abstractmethod
from src.domain.models.pre_alignment import PipelinePreAlignmentData


class PubMedDataPort(ABC):
    """
    Driven / Outbound port for fetching preliminary biomedical alignment results
    from the pubmed-integration microservice.
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
