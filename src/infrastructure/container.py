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
from src.domain.ports.pubmed_port import PubMedDataPort
from src.domain.ports.llm_reasoning_port import LLMReasoningPort
from src.domain.ports.biological_objects_port import BiologicalObjectsPort
from src.application.use_cases.alignment_use_case import GenerateAlignmentProposalUseCase
from src.application.use_cases.impl.alignment_use_case_impl import GenerateAlignmentProposalUseCaseImpl
from src.application.services.alignment import (
    DirectMatchingService,
    DatabaseMatchingService,
    LiteratureEvidenceService,
    AIResolutionService,
)
from src.infrastructure.adapters.pubmed.pubmed_http_adapter import PubMedHttpAdapter
from src.infrastructure.adapters.biological_objects.biological_objects_http_adapter import BiologicalObjectsHttpAdapter
from src.infrastructure.adapters.llm.llm_adapter_factory import LLMAdapterFactory


class Container:
    """
    Dependency Injection Container.
    Assembles driven adapters and wires application domain services and use cases.
    """

    def __init__(self):
        # 1. Ports / Adapters
        self._pubmed_port: PubMedDataPort = PubMedHttpAdapter()
        self._biological_objects_port: BiologicalObjectsPort = BiologicalObjectsHttpAdapter()
        self._llm_port: LLMReasoningPort = LLMAdapterFactory.create_adapter()

        # 2. Application Services (Alignment context)
        self._direct_matching_service = DirectMatchingService()
        self._database_matching_service = DatabaseMatchingService(
            biological_objects_port=self._biological_objects_port
        )
        self._literature_evidence_service = LiteratureEvidenceService(
            pubmed_port=self._pubmed_port
        )
        self._ai_resolution_service = AIResolutionService(
            llm_port=self._llm_port
        )

        # 3. Application Use Cases (Orchestrators)
        self._alignment_use_case: GenerateAlignmentProposalUseCase = GenerateAlignmentProposalUseCaseImpl(
            pubmed_port=self._pubmed_port,
            direct_matching_service=self._direct_matching_service,
            database_matching_service=self._database_matching_service,
            literature_evidence_service=self._literature_evidence_service,
            ai_resolution_service=self._ai_resolution_service
        )

    def get_alignment_use_case(self) -> GenerateAlignmentProposalUseCase:
        return self._alignment_use_case

    def get_pubmed_port(self) -> PubMedDataPort:
        return self._pubmed_port

    def get_biological_objects_port(self) -> BiologicalObjectsPort:
        return self._biological_objects_port

    def get_llm_port(self) -> LLMReasoningPort:
        return self._llm_port

    def get_direct_matching_service(self) -> DirectMatchingService:
        return self._direct_matching_service

    def get_database_matching_service(self) -> DatabaseMatchingService:
        return self._database_matching_service

    def get_literature_evidence_service(self) -> LiteratureEvidenceService:
        return self._literature_evidence_service

    def get_ai_resolution_service(self) -> AIResolutionService:
        return self._ai_resolution_service


# Singleton container instance
container = Container()
