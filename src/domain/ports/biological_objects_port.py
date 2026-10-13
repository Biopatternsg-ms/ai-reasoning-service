from abc import ABC, abstractmethod
from typing import List
from src.domain.models.biological_object import BiologicalObjectDomain


class BiologicalObjectsPort(ABC):
    """
    Driven port for interacting with the search-biological-objects service.
    """

    @abstractmethod
    async def search_by_synonym(self, synonym: str, user_id: str) -> List[BiologicalObjectDomain]:
        """
        Retrieves matching biological objects by synonym.
        """
        pass
