#
# Copyright © 2026 biopatternsg (biopatternsg@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
