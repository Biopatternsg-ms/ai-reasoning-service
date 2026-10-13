import logging
from typing import Optional

from src.application.use_cases.alignment_use_case import GenerateAlignmentProposalUseCase
from src.application.services.alignment import (
    DirectMatchingService,
    DatabaseMatchingService,
    LiteratureEvidenceService,
    AIResolutionService,
)
from src.domain.ports.pubmed_port import PubMedDataPort
from src.domain.ports.biological_objects_port import BiologicalObjectsPort
from src.domain.ports.llm_reasoning_port import LLMReasoningPort
from src.domain.models.alignment_proposal import AlignmentProposal
from src.domain.models.pre_alignment import PipelinePreAlignmentData
from src.domain.exceptions.exceptions import AlignmentException, EntityValidationException

logger = logging.getLogger(__name__)


class GenerateAlignmentProposalUseCaseImpl(GenerateAlignmentProposalUseCase):
    """
    Concrete implementation of GenerateAlignmentProposalUseCase.
    Orchestrates the 3-stage biological entity alignment pipeline by coordinating
    specialized single-responsibility domain services:
    - Stage 1: DirectMatchingService (Deterministic, zero tokens).
    - Stage 2: DatabaseMatchingService (BiopatternsG search-biological-objects).
    - Stage 3: LiteratureEvidenceService & AIResolutionService (PubMed & LLM reasoning).
    """

    def __init__(
        self,
        pubmed_port: PubMedDataPort,
        biological_objects_port: Optional[BiologicalObjectsPort] = None,
        llm_port: Optional[LLMReasoningPort] = None,
        direct_matching_service: Optional[DirectMatchingService] = None,
        database_matching_service: Optional[DatabaseMatchingService] = None,
        literature_evidence_service: Optional[LiteratureEvidenceService] = None,
        ai_resolution_service: Optional[AIResolutionService] = None,
    ):
        self.pubmed_port = pubmed_port

        # Initialize or assign specialized services
        self.direct_matching_service = direct_matching_service or DirectMatchingService()
        self.database_matching_service = database_matching_service or (
            DatabaseMatchingService(biological_objects_port) if biological_objects_port else None
        )
        self.literature_evidence_service = literature_evidence_service or LiteratureEvidenceService(pubmed_port)
        self.ai_resolution_service = ai_resolution_service or (
            AIResolutionService(llm_port) if llm_port else None
        )

    async def execute(self, pipeline_id: str, user_id: str) -> AlignmentProposal:
        """
        Coordinates the alignment pipeline across specialized services:
        1. Validates inputs.
        2. Retrieves preliminary alignment data.
        3. Stage 1: Resolves deterministic direct matches.
        4. Stage 2: Resolves ambiguous candidates against BiopatternsG database.
        5. Stage 3: Collects literature evidence and resolves remaining entities with AI.
        6. Consolidates and returns the AlignmentProposal.
        """
        if not pipeline_id or not pipeline_id.strip():
            raise EntityValidationException("Pipeline ID cannot be empty.")
        if not user_id or not user_id.strip():
            raise EntityValidationException("User ID cannot be empty.")

        clean_pipeline_id = pipeline_id.strip()
        clean_user_id = user_id.strip()

        logger.info(f"Executing alignment proposal for pipelineId: {clean_pipeline_id}, userId: {clean_user_id}")

        # 1. Fetch preliminary classification data from pubmed port
        try:
            pre_data: PipelinePreAlignmentData = await self.pubmed_port.get_aligned_results(
                pipeline_id=clean_pipeline_id,
                user_id=clean_user_id
            )
        except Exception as e:
            logger.error(f"Failed to fetch pre-alignment data for pipeline '{clean_pipeline_id}': {str(e)}")
            raise AlignmentException(f"Failed to retrieve pre-alignment data: {str(e)}")

        # 2. STAGE 1: Deterministic direct matching (Zero LLM Tokens)
        direct_items, pending_ambiguous, processed_symbols = self.direct_matching_service.process_direct_matches(pre_data)

        # 3. STAGE 2: BiopatternsG knowledge base matching (search-biological-objects)
        db_items, ambiguous_requiring_ai = [], pending_ambiguous
        if self.database_matching_service:
            db_items, ambiguous_requiring_ai, db_processed = await self.database_matching_service.process_database_matches(
                ambiguous_entities=pending_ambiguous,
                user_id=clean_user_id
            )
            processed_symbols.update(db_processed)

        # 4. Filter unaligned entities not yet processed
        entities_to_resolve = [
            s.strip() for s in pre_data.no_aligned
            if s.strip() and s.strip().upper() not in processed_symbols
        ]

        # 5. STAGE 3: Literature evidence retrieval
        literature_evidence = await self.literature_evidence_service.fetch_literature_evidence(
            pipeline_id=clean_pipeline_id,
            entities=entities_to_resolve,
            user_id=clean_user_id
        )

        # 6. STAGE 3: AI-Assisted resolution & mapping
        unaligned_items, ambiguous_items = [], []
        if self.ai_resolution_service:
            unaligned_items, ambiguous_items = await self.ai_resolution_service.resolve_entities(
                entities_to_resolve=entities_to_resolve,
                ambiguous_to_resolve=ambiguous_requiring_ai,
                literature_evidence=literature_evidence
            )

        # 7. Consolidate results into domain proposal
        consolidated_objects = direct_items + db_items + unaligned_items + ambiguous_items

        logger.info(
            f"Proposal generated successfully for pipelineId {clean_pipeline_id}: "
            f"{len(consolidated_objects)} objects processed "
            f"({len(direct_items)} direct, {len(db_items)} db matched, "
            f"{len(unaligned_items) + len(ambiguous_items)} AI evaluated)."
        )

        return AlignmentProposal(
            pipeline_id=clean_pipeline_id,
            objects=consolidated_objects
        )
