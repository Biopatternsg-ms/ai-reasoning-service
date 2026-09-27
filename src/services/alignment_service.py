import logging
from typing import List, Dict, Set, Tuple
from src.clients.pubmed_client import PubmedClient
from src.clients.llm_gateway import LLMGateway
from src.models.alignment_dto import AlignedItem, AlignmentProposalResponse
from src.models.pubmed_dto import AlignedResultDTO, AlignedAsDTO
from src.prompts.alignment_prompt import (
    ALIGNMENT_SYSTEM_INSTRUCTION,
    build_alignment_prompt
)

logger = logging.getLogger(__name__)


class AlignmentService:
    def __init__(self, pubmed_client: PubmedClient = None, llm_gateway: LLMGateway = None):
        self.pubmed_client = pubmed_client or PubmedClient()
        self.llm_gateway = llm_gateway or LLMGateway()

    async def generate_alignment_proposal(self, pipeline_id: str, user_id: str) -> AlignmentProposalResponse:
        """
        Main orchestrator method coordinating the alignment proposal pipeline:
        1. Queries pubmed-integration.
        2. Processes direct matches (zero token cost).
        3. Identifies entities requiring AI inference.
        4. Queries the LLM engine.
        5. Maps unaligned and ambiguous items with scientific rationale or fallbacks.
        6. Consolidates and returns the final response for the UI.
        """
        logger.info(f"Starting alignment proposal for pipelineId: {pipeline_id}, userId: {user_id}")

        # 1. Fetch pre-classified data from pubmed-integration
        pubmed_data = await self._fetch_aligned_results(pipeline_id, user_id)

        # 2. Process direct matches (zero token cost)
        direct_items, processed_symbols = self._process_direct_matches(pubmed_data.aligned)

        # 3. Filter entities requiring AI inference
        entities_to_resolve, ambiguous_to_resolve = self._filter_pending_entities(
            pubmed_data=pubmed_data,
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

        logger.info(f"Proposal generated successfully for pipelineId {pipeline_id}: {len(consolidated_objects)} objects processed.")
        return AlignmentProposalResponse(
            pipelineId=pipeline_id,
            objects=consolidated_objects
        )

    # -------------------------------------------------------------------------
    # Specialized Private Methods (Single Responsibility Principle)
    # -------------------------------------------------------------------------

    async def _fetch_aligned_results(self, pipeline_id: str, user_id: str) -> AlignedResultDTO:
        """Queries preliminary alignment data from pubmed-integration."""
        return await self.pubmed_client.get_aligned_results(pipeline_id, user_id=user_id)

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
                    status="DIRECT_MATCH",
                    reason="Direct match in PubTator synonyms"
                )
            )
            processed.add(sym.upper())

        return direct_items, processed

    def _filter_pending_entities(
        self,
        pubmed_data: AlignedResultDTO,
        processed_symbols: Set[str]
    ) -> Tuple[List[str], List[AlignedAsDTO]]:
        """
        Filters and returns entities that had no direct match and require AI resolution.
        """
        entities_to_resolve = [
            s for s in pubmed_data.no_aligned
            if s.upper() not in processed_symbols
        ]
        ambiguous_to_resolve = [
            a for a in pubmed_data.aligned_as
            if a.expert_object_name.upper() not in processed_symbols
        ]
        return entities_to_resolve, ambiguous_to_resolve

    async def _query_llm_resolutions(
        self,
        entities_to_resolve: List[str],
        ambiguous_to_resolve: List[AlignedAsDTO]
    ) -> Dict[str, Dict[str, str]]:
        """
        Builds the micro-prompt and queries the LLM Gateway to resolve ambiguities.
        Returns a dictionary indexed by uppercase symbol:
        { "TATA": { "aligned": "TBP", "reason": "..." } }
        """
        if not entities_to_resolve and not ambiguous_to_resolve:
            return {}

        prompt_content = build_alignment_prompt(
            no_aligned=entities_to_resolve,
            aligned_as=[a.model_dump() for a in ambiguous_to_resolve]
        )
        logger.info(
            f"Sending alignment micro-prompt to LLM for {len(entities_to_resolve)} unaligned "
            f"and {len(ambiguous_to_resolve)} ambiguous entities"
        )

        resolutions: Dict[str, Dict[str, str]] = {}
        try:
            ai_response = await self.llm_gateway.generate_json(
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
            logger.error(
                f"Error during LLM inference: {str(e)}. Safe fallbacks will be activated."
            )

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
                        status="RESOLVED_BY_AI",
                        reason=res["reason"]
                    )
                )
            else:
                items.append(
                    AlignedItem(
                        current=sym,
                        aligned=sym,
                        status="UNRESOLVED",
                        reason="No canonical substitute identified; original retained"
                    )
                )
        return items

    def _map_ambiguous_entities(
        self,
        ambiguous: List[AlignedAsDTO],
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
                        status="RESOLVED_BY_AI",
                        reason=res["reason"]
                    )
                )
            else:
                fallback_aligned = amb.alternative_ids[0] if amb.alternative_ids else sym
                items.append(
                    AlignedItem(
                        current=sym,
                        aligned=fallback_aligned,
                        status="UNRESOLVED",
                        reason="Selected default candidate from alternatives"
                    )
                )
        return items
