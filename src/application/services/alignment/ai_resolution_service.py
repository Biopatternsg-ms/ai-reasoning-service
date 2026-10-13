import logging
from typing import List, Dict, Any, Optional, Tuple

from src.domain.ports.llm_reasoning_port import LLMReasoningPort
from src.domain.models.entity import AlignedItem, AlignmentStatus
from src.domain.models.pre_alignment import AmbiguousEntityItem
from src.application.prompts.alignment_prompt import (
    ALIGNMENT_SYSTEM_INSTRUCTION,
    build_alignment_prompt,
)

logger = logging.getLogger(__name__)


class AIResolutionService:
    """
    STAGE 3: AI-Assisted Resolution with Literature Evidence & Scientific Justification.
    Builds micro-prompts with contextual abstracts, queries the LLMReasoningPort,
    and maps the structured JSON suggestions to domain AlignedItem models.
    """

    def __init__(self, llm_port: LLMReasoningPort):
        self.llm_port = llm_port

    async def resolve_entities(
        self,
        entities_to_resolve: List[str],
        ambiguous_to_resolve: List[AmbiguousEntityItem],
        literature_evidence: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[AlignedItem], List[AlignedItem]]:
        """
        Executes AI reasoning for unaligned and ambiguous entities.

        Returns:
        - Tuple of (unaligned_items, ambiguous_items) as domain AlignedItem lists.
        """
        if not entities_to_resolve and not ambiguous_to_resolve:
            return [], []

        resolutions = await self._query_llm_resolutions(
            entities_to_resolve=entities_to_resolve,
            ambiguous_to_resolve=ambiguous_to_resolve,
            literature_evidence=literature_evidence
        )

        unaligned_items = self._map_unaligned_entities(
            entities=entities_to_resolve,
            resolutions=resolutions
        )

        ambiguous_items = self._map_ambiguous_entities(
            ambiguous=ambiguous_to_resolve,
            resolutions=resolutions
        )

        return unaligned_items, ambiguous_items

    async def _query_llm_resolutions(
        self,
        entities_to_resolve: List[str],
        ambiguous_to_resolve: List[AmbiguousEntityItem],
        literature_evidence: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Builds the micro-prompt and queries the LLMReasoningPort.
        Returns a dictionary indexed by uppercase symbol:
        { "TATA": { "aligned": "TBP", "reason": "...", "pubmed_ids": [...] } }
        """
        prompt_content = build_alignment_prompt(
            no_aligned=entities_to_resolve,
            aligned_as=[
                {"expert_object_name": a.expert_object_name, "alternative_ids": a.alternative_ids}
                for a in ambiguous_to_resolve
            ],
            literature_evidence=literature_evidence
        )
        logger.info(
            f"[AIResolutionService] Sending micro-prompt for {len(entities_to_resolve)} unaligned "
            f"and {len(ambiguous_to_resolve)} ambiguous entities (with {len(literature_evidence or [])} literature entries)"
        )

        resolutions: Dict[str, Dict[str, Any]] = {}
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

                    raw_pubmed_ids = res.get("pubmedIds") or res.get("pubmed_ids") or []
                    if isinstance(raw_pubmed_ids, list):
                        cleaned_pmids = [str(p).strip() for p in raw_pubmed_ids if str(p).strip()]
                    else:
                        cleaned_pmids = []

                    resolutions[curr.upper()] = {
                        "aligned": res.get("aligned", curr).strip(),
                        "reason": full_reason,
                        "pubmed_ids": cleaned_pmids
                    }
        except Exception as e:
            logger.error(f"[AIResolutionService] Error during LLM inference: {str(e)}. Safe fallbacks will be activated.")

        return resolutions

    def _map_unaligned_entities(
        self,
        entities: List[str],
        resolutions: Dict[str, Dict[str, Any]]
    ) -> List[AlignedItem]:
        """
        Maps each unaligned entity with the AI suggestion, justification, and supporting PubMed IDs.
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
                        reason=res["reason"],
                        pubmed_ids=res.get("pubmed_ids", [])
                    )
                )
            else:
                items.append(
                    AlignedItem(
                        current=sym,
                        aligned=sym,
                        status=AlignmentStatus.UNRESOLVED,
                        reason="No canonical substitute identified; original retained",
                        pubmed_ids=[]
                    )
                )
        return items

    def _map_ambiguous_entities(
        self,
        ambiguous: List[AmbiguousEntityItem],
        resolutions: Dict[str, Dict[str, Any]]
    ) -> List[AlignedItem]:
        """
        Maps each ambiguous entity with the AI canonical choice, justification, and supporting PubMed IDs.
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
                        reason=res["reason"],
                        pubmed_ids=res.get("pubmed_ids", [])
                    )
                )
            else:
                fallback_aligned = amb.alternative_ids[0] if amb.alternative_ids else sym
                items.append(
                    AlignedItem(
                        current=sym,
                        aligned=fallback_aligned,
                        status=AlignmentStatus.UNRESOLVED,
                        reason="Selected default candidate from alternatives",
                        pubmed_ids=[]
                    )
                )
        return items
