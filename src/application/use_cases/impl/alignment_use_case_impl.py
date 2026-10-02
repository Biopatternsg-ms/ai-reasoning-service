import logging
from typing import List, Dict, Set, Tuple

from src.application.use_cases.alignment_use_case import GenerateAlignmentProposalUseCase
from src.domain.ports.pubmed_port import PubMedDataPort
from src.domain.ports.llm_reasoning_port import LLMReasoningPort
from src.domain.models.entity import AlignedItem, AlignmentStatus
from src.domain.models.alignment_proposal import AlignmentProposal
from src.domain.models.pre_alignment import PipelinePreAlignmentData, AmbiguousEntityItem
from src.domain.exceptions.exceptions import AlignmentException, EntityValidationException
from src.application.prompts.alignment_prompt import (
    ALIGNMENT_SYSTEM_INSTRUCTION,
    build_alignment_prompt,
)

logger = logging.getLogger(__name__)


class GenerateAlignmentProposalUseCaseImpl(GenerateAlignmentProposalUseCase):
    """
    Concrete implementation of GenerateAlignmentProposalUseCase.
    Orchestrates the domain workflow using driven ports (PubMedDataPort, LLMReasoningPort).
    """

    def __init__(self, pubmed_port: PubMedDataPort, llm_port: LLMReasoningPort):
        self.pubmed_port = pubmed_port
        self.llm_port = llm_port

    async def execute(self, pipeline_id: str, user_id: str) -> AlignmentProposal:
        """
        Coordinates the complete alignment proposal pipeline:
        1. Validates inputs.
        2. Queries preliminary alignment data via PubMedDataPort.
        3. Processes direct matches (zero LLM token cost).
        4. Identifies entities requiring AI inference.
        5. Queries LLMReasoningPort with strict scientific heuristics and fallback safety.
        6. Maps unaligned and ambiguous items.
        7. Returns the consolidated AlignmentProposal domain aggregate.
        """
        if not pipeline_id or not pipeline_id.strip():
            raise EntityValidationException("Pipeline ID cannot be empty.")
        if not user_id or not user_id.strip():
            raise EntityValidationException("User ID cannot be empty.")

        logger.info(f"Executing alignment proposal for pipelineId: {pipeline_id}, userId: {user_id}")

        # 1. Fetch pre-classified data from pubmed port
        try:
            pre_data: PipelinePreAlignmentData = await self.pubmed_port.get_aligned_results(
                pipeline_id=pipeline_id.strip(),
                user_id=user_id.strip()
            )
        except Exception as e:
            logger.error(f"Failed to fetch pre-alignment data for pipeline '{pipeline_id}': {str(e)}")
            raise AlignmentException(f"Failed to retrieve pre-alignment data: {str(e)}")

        # 2. Process direct matches (zero token cost)
        direct_items, processed_symbols = self._process_direct_matches(pre_data.aligned)

        # 3. Filter entities requiring AI inference
        entities_to_resolve, ambiguous_to_resolve = self._filter_pending_entities(
            pre_data=pre_data,
            processed_symbols=processed_symbols
        )

        # 4. Query LLM resolutions (with fallback handling)
        ai_resolutions = await self._query_llm_resolutions(
            entities_to_resolve=entities_to_resolve,
            ambiguous_to_resolve=ambiguous_to_resolve
        )

        # 5. Map unaligned entities (no_aligned)
        unaligned_items = self._map_unaligned_entities(
            entities=entities_to_resolve,
            resolutions=ai_resolutions
        )

        # 6. Map ambiguous entities (aligned_as)
        ambiguous_items = self._map_ambiguous_entities(
            ambiguous=ambiguous_to_resolve,
            resolutions=ai_resolutions
        )

        # 7. Consolidate final output
        consolidated_objects = direct_items + unaligned_items + ambiguous_items

        logger.info(
            f"Proposal generated successfully for pipelineId {pipeline_id}: "
            f"{len(consolidated_objects)} objects processed."
        )

        return AlignmentProposal(
            pipeline_id=pipeline_id.strip(),
            objects=consolidated_objects
        )

    # -------------------------------------------------------------------------
    # Specialized Private Methods (Single Responsibility Principle)
    # -------------------------------------------------------------------------

    def _process_direct_matches(self, aligned_symbols: List[str]) -> Tuple[List[AlignedItem], Set[str]]:
        """
        Processes entities with direct matches in official PubTator synonyms.
        Returns a list of AlignedItem and an uppercase set of processed symbols.
        """
        direct_items: List[AlignedItem] = []
        processed: Set[str] = set()

        for sym in aligned_symbols:
            direct_items.append(
                AlignedItem(
                    current=sym,
                    aligned=sym,
                    status=AlignmentStatus.DIRECT_MATCH,
                    reason="Direct match in PubTator synonyms"
                )
            )
            processed.add(sym.upper())

        return direct_items, processed

    def _filter_pending_entities(
        self,
        pre_data: PipelinePreAlignmentData,
        processed_symbols: Set[str]
    ) -> Tuple[List[str], List[AmbiguousEntityItem]]:
        """
        Filters and returns entities that had no direct match and require AI resolution.
        """
        entities_to_resolve = [
            s for s in pre_data.no_aligned
            if s.upper() not in processed_symbols
        ]
        ambiguous_to_resolve = [
            a for a in pre_data.aligned_as
            if a.expert_object_name.upper() not in processed_symbols
        ]
        return entities_to_resolve, ambiguous_to_resolve

    async def _query_llm_resolutions(
        self,
        entities_to_resolve: List[str],
        ambiguous_to_resolve: List[AmbiguousEntityItem]
    ) -> Dict[str, Dict[str, str]]:
        """
        Builds the micro-prompt and queries the LLMReasoningPort to resolve ambiguities.
        Returns a dictionary indexed by uppercase symbol:
        { "TATA": { "aligned": "TBP", "reason": "..." } }
        """
        if not entities_to_resolve and not ambiguous_to_resolve:
            return {}

        prompt_content = build_alignment_prompt(
            no_aligned=entities_to_resolve,
            aligned_as=[
                {"expert_object_name": a.expert_object_name, "alternative_ids": a.alternative_ids}
                for a in ambiguous_to_resolve
            ]
        )
        logger.info(
            f"Sending alignment micro-prompt to LLM for {len(entities_to_resolve)} unaligned "
            f"and {len(ambiguous_to_resolve)} ambiguous entities"
        )

        resolutions: Dict[str, Dict[str, str]] = {}
        try:
            ai_response = await self.llm_port.generate_json(
                prompt=prompt_content,
                system_instruction=ALIGNMENT_SYSTEM_INSTRUCTION
            )

            resolutions_list = ai_response.get("resolutions", [])
            for res in resolutions_list:
                curr = res.get("current", "").strip()
                if curr:
                    reason = res.get("reason", "Resolved by AI").strip()
                    criterion = res.get("criterion", "").strip()
                    if criterion and criterion.lower() != "unresolved":
                        full_reason = f"{reason} [Criterion: {criterion}]"
                    else:
                        full_reason = reason
                    resolutions[curr.upper()] = {
                        "aligned": res.get("aligned", curr).strip(),
                        "reason": full_reason
                    }
        except Exception as e:
            logger.error(f"Error during LLM inference: {str(e)}. Safe fallbacks will be activated.")

        return resolutions

    def _map_unaligned_entities(
        self,
        entities: List[str],
        resolutions: Dict[str, Dict[str, str]]
    ) -> List[AlignedItem]:
        """
        Maps each unaligned entity with the AI suggestion or its UNRESOLVED fallback.
        """
        items: List[AlignedItem] = []
        for sym in entities:
            res = resolutions.get(sym.upper())
            if res:
                items.append(
                    AlignedItem(
                        current=sym,
                        aligned=res["aligned"],
                        status=AlignmentStatus.RESOLVED_BY_AI,
                        reason=res["reason"]
                    )
                )
            else:
                items.append(
                    AlignedItem(
                        current=sym,
                        aligned=sym,
                        status=AlignmentStatus.UNRESOLVED,
                        reason="No canonical substitute identified; original retained"
                    )
                )
        return items

    def _map_ambiguous_entities(
        self,
        ambiguous: List[AmbiguousEntityItem],
        resolutions: Dict[str, Dict[str, str]]
    ) -> List[AlignedItem]:
        """
        Maps each ambiguous entity with the AI canonical choice or first candidate fallback.
        """
        items: List[AlignedItem] = []
        for amb in ambiguous:
            sym = amb.expert_object_name
            res = resolutions.get(sym.upper())
            if res:
                items.append(
                    AlignedItem(
                        current=sym,
                        aligned=res["aligned"],
                        status=AlignmentStatus.RESOLVED_BY_AI,
                        reason=res["reason"]
                    )
                )
            else:
                fallback_aligned = amb.alternative_ids[0] if amb.alternative_ids else sym
                items.append(
                    AlignedItem(
                        current=sym,
                        aligned=fallback_aligned,
                        status=AlignmentStatus.UNRESOLVED,
                        reason="Selected default candidate from alternatives"
                    )
                )
        return items
