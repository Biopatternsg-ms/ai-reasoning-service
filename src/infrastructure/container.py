from src.domain.ports.pubmed_port import PubMedDataPort
from src.domain.ports.llm_reasoning_port import LLMReasoningPort
from src.application.use_cases.alignment_use_case import GenerateAlignmentProposalUseCase
from src.application.use_cases.impl.alignment_use_case_impl import GenerateAlignmentProposalUseCaseImpl
from src.infrastructure.adapters.pubmed.pubmed_http_adapter import PubMedHttpAdapter
from src.infrastructure.adapters.llm.llm_adapter_factory import LLMAdapterFactory


class Container:
    """
    Dependency Injection Container.
    Assembles driven adapters and wires them into application use cases.
    """

    def __init__(self):
        self._pubmed_port: PubMedDataPort = PubMedHttpAdapter()
        self._llm_port: LLMReasoningPort = LLMAdapterFactory.create_adapter()
        self._alignment_use_case: GenerateAlignmentProposalUseCase = GenerateAlignmentProposalUseCaseImpl(
            pubmed_port=self._pubmed_port,
            llm_port=self._llm_port
        )

    def get_alignment_use_case(self) -> GenerateAlignmentProposalUseCase:
        return self._alignment_use_case

    def get_pubmed_port(self) -> PubMedDataPort:
        return self._pubmed_port

    def get_llm_port(self) -> LLMReasoningPort:
        return self._llm_port


# Singleton container instance
container = Container()
