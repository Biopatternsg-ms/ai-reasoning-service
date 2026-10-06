import logging
from typing import List, Dict, Set, Tuple, Optional, Any

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

        # STAGE 1: Deterministic matching (Zero LLM Tokens)
        # Evaluates entities with direct synonym match or already pre-aligned
        direct_items, ambiguous_to_resolve, processed_symbols = self._process_direct_matches(pre_data)

        # STAGE 2: AI-Assisted Resolution with Literature Evidence & Scientific Justification
        # Filter unaligned entities not yet processed
        entities_to_resolve = self._filter_pending_entities(
            no_aligned=pre_data.no_aligned,
            processed_symbols=processed_symbols
        )

        # Fetch literature evidence (abstracts and interaction events) for unaligned entities
        literature_evidence = await self._fetch_literature_evidence(
            pipeline_id=pipeline_id.strip(),
            entities=entities_to_resolve,
            user_id=user_id.strip()
        )

        # Query LLM resolutions only for pending entities
        ai_resolutions = await self._query_llm_resolutions(
            entities_to_resolve=entities_to_resolve,
            ambiguous_to_resolve=ambiguous_to_resolve,
            literature_evidence=literature_evidence
        )

        # Map unaligned entities (no_aligned) with AI proposal + justification
        unaligned_items = self._map_unaligned_entities(
            entities=entities_to_resolve,
            resolutions=ai_resolutions
        )

        # Map ambiguous entities (aligned_as without direct match) with AI choice + justification
        ambiguous_items = self._map_ambiguous_entities(
            ambiguous=ambiguous_to_resolve,
            resolutions=ai_resolutions
        )

        # Consolidate Stage 1 and Stage 2 outputs
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

    def _process_direct_matches(
        self,
        pre_data: PipelinePreAlignmentData
    ) -> Tuple[List[AlignedItem], List[AmbiguousEntityItem], Set[str]]:
        """
        STAGE 1: Deterministic matching without AI invocation (Zero LLM Tokens).
        1. Evaluates entities already classified in 'aligned'.
        2. Evaluates entities in 'aligned_as' (synonyms list):
           If the entity symbol exactly matches one of the candidate synonyms (case-insensitive),
           it is resolved immediately as DIRECT_MATCH without calling the LLM.
        
        Returns:
        - List of resolved AlignedItem (Stage 1 direct matches).
        - List of truly ambiguous entities that did NOT have an exact match in their synonyms.
        - Set of uppercase processed symbols.
        """
        direct_items: List[AlignedItem] = []
        ambiguous_requiring_ai: List[AmbiguousEntityItem] = []
        processed: Set[str] = set()

        # 1. Matches already recognized in aligned
        for sym in pre_data.aligned:
            sym_clean = sym.strip()
            if sym_clean and sym_clean.upper() not in processed:
                direct_items.append(
                    AlignedItem(
                        current=sym_clean,
                        aligned=sym_clean,
                        status=AlignmentStatus.DIRECT_MATCH,
                        reason="Direct match in official PubTator synonyms"
                    )
                )
                processed.add(sym_clean.upper())

        # 2. Check aligned_as (synonyms/alternatives list) for exact matches
        for amb in pre_data.aligned_as:
            name = amb.expert_object_name.strip()
            if name.upper() in processed:
                continue

            # Check if name exists directly inside candidate alternatives/synonyms
            exact_match_found = False
            for cand in amb.alternative_ids:
                if cand.strip().upper() == name.upper():
                    direct_items.append(
                        AlignedItem(
                            current=name,
                            aligned=cand.strip(),
                            status=AlignmentStatus.DIRECT_MATCH,
                            reason="Exact match found within candidate synonyms list"
                        )
                    )
                    processed.add(name.upper())
                    exact_match_found = True
                    break

            if not exact_match_found:
                # No exact match: this entity requires Stage 2 AI reasoning & justification
                ambiguous_requiring_ai.append(amb)

        return direct_items, ambiguous_requiring_ai, processed

    def _filter_pending_entities(
        self,
        no_aligned: List[str],
        processed_symbols: Set[str]
    ) -> List[str]:
        """
        Filters and returns entities in 'no_aligned' requiring Stage 2 AI resolution.
        """
        return [
            s.strip() for s in no_aligned
            if s.strip() and s.strip().upper() not in processed_symbols
        ]

    async def _fetch_literature_evidence(
        self,
        pipeline_id: str,
        entities: List[str],
        user_id: str
    ) -> List[Dict[str, any]]:
        """
        Retrieves knowledge base events and publication abstracts for unaligned entities.
        Limits to top 3 PubMed IDs per entity to optimize context window and latency.
        """
        if not entities:
            return []

        literature_list = []
        for term in entities:
            try:
                # 1. Fetch interaction events for this term
                events = await self.pubmed_port.get_kb_events_by_term(
                    pipeline_id=pipeline_id,
                    term=term,
                    user_id=user_id
                )

                # 2. Extract unique PubMed IDs (limit to top 3)
                collected_pmids = []
                event_summaries = []
                for ev in events:
                    event_summaries.append(f"{ev.first} {ev.relation} {ev.second}")
                    for pmid in ev.pubmed_ids:
                        clean_pmid = pmid.strip()
                        if clean_pmid and clean_pmid not in collected_pmids:
                            collected_pmids.append(clean_pmid)

                top_pmids = collected_pmids[:3]

                # 3. Fetch publications (titles and abstracts)
                pubs = []
                if top_pmids:
                    pubs = await self.pubmed_port.get_publications_by_pmids(
                        pmids=top_pmids,
                        user_id=user_id
                    )

                if pubs or event_summaries:
                    literature_list.append({
                        "symbol": term,
                        "events": event_summaries[:5],
                        "publications": [
                            {
                                "pmid": p.pmid,
                                "title": p.title or "",
                                "abstractSnippet": (p.text[:400] + "...") if p.text and len(p.text) > 400 else (p.text or "")
                            }
                            for p in pubs
                        ]
                    })
            except Exception as e:
                logger.warning(f"Could not retrieve literature evidence for term '{term}': {str(e)}")

        return literature_list

    async def _query_llm_resolutions(
        self,
        entities_to_resolve: List[str],
        ambiguous_to_resolve: List[AmbiguousEntityItem],
        literature_evidence: Optional[List[Dict[str, any]]] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Builds the micro-prompt with literature evidence and queries the LLMReasoningPort.
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
            ],
            literature_evidence=literature_evidence
        )
        logger.info(
            f"Sending alignment micro-prompt to LLM for {len(entities_to_resolve)} unaligned "
            f"and {len(ambiguous_to_resolve)} ambiguous entities (with {len(literature_evidence or [])} literature entries)"
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

                    # Extract supporting pubmedIds list (defaulting to empty list if none)
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
            logger.error(f"Error during LLM inference: {str(e)}. Safe fallbacks will be activated.")

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
