import logging
from typing import List, Set, Tuple

from src.domain.models.entity import AlignedItem, AlignmentStatus
from src.domain.models.pre_alignment import PipelinePreAlignmentData, AmbiguousEntityItem

logger = logging.getLogger(__name__)


class DirectMatchingService:
    """
    STAGE 1: Deterministic matching without AI invocation (Zero LLM Tokens).
    1. Evaluates entities already classified in 'aligned'.
    2. Evaluates entities in 'aligned_as' (synonyms list):
       If the entity symbol exactly matches one of the candidate synonyms (case-insensitive),
       it is resolved immediately as DIRECT_MATCH without calling the LLM.
    """

    def process_direct_matches(
        self,
        pre_data: PipelinePreAlignmentData
    ) -> Tuple[List[AlignedItem], List[AmbiguousEntityItem], Set[str]]:
        """
        Processes preliminary data to extract direct matches.

        Returns:
        - List of resolved AlignedItem (Stage 1 direct matches).
        - List of truly ambiguous entities that did NOT have an exact match in their synonyms.
        - Set of uppercase processed symbols.
        """
        direct_items: List[AlignedItem] = []
        ambiguous_requiring_resolution: List[AmbiguousEntityItem] = []
        processed: Set[str] = set()

        # 1. Matches already recognized in 'aligned'
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

        # 2. Check 'aligned_as' (synonyms/alternatives list) for exact matches
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
                # No exact match: this entity requires Stage 2 or Stage 3 resolution
                ambiguous_requiring_resolution.append(amb)

        logger.debug(
            f"[DirectMatchingService] Resolved {len(direct_items)} direct items, "
            f"{len(ambiguous_requiring_resolution)} ambiguous entities pending."
        )

        return direct_items, ambiguous_requiring_resolution, processed
