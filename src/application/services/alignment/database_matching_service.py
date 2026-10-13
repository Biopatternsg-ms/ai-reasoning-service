import logging
from typing import List, Set, Tuple, Optional

from src.domain.ports.biological_objects_port import BiologicalObjectsPort
from src.domain.models.entity import AlignedItem, AlignmentStatus
from src.domain.models.pre_alignment import AmbiguousEntityItem
from src.domain.models.biological_object import BiologicalObjectDomain

logger = logging.getLogger(__name__)


class DatabaseMatchingService:
    """
    STAGE 2: Intermediate deterministic resolution against BiopatternsG knowledge base.
    For each ambiguous entity, queries /search-by-synonym/{synonym} using expertObjectName.
    If the first returned biological object has a synonym (or symbol) matching any candidate in alternative_ids:
    - Resolves as RESOLVED_BY_DATABASE.
    - Provides reason citing BiopatternsG database with HGNC and UniProt IDs (if available).
    - Sets pubmedIds to [].
    """

    def __init__(self, biological_objects_port: BiologicalObjectsPort):
        self.biological_objects_port = biological_objects_port

    async def process_database_matches(
        self,
        ambiguous_entities: List[AmbiguousEntityItem],
        user_id: str
    ) -> Tuple[List[AlignedItem], List[AmbiguousEntityItem], Set[str]]:
        """
        Evaluates ambiguous entities against the BiopatternsG biological objects database.

        Returns:
        - List of resolved AlignedItem.
        - List of unresolved ambiguous entities that need AI reasoning.
        - Set of uppercase processed symbols.
        """
        resolved_items: List[AlignedItem] = []
        unresolved_ambiguous: List[AmbiguousEntityItem] = []
        processed: Set[str] = set()

        logger.info(
            f"[DatabaseMatchingService] Evaluating {len(ambiguous_entities)} ambiguous entities against "
            f"BiopatternsG database (search-biological-objects)"
        )

        for amb in ambiguous_entities:
            expert_name = amb.expert_object_name.strip()
            if not expert_name:
                unresolved_ambiguous.append(amb)
                continue

            try:
                bio_objects = await self.biological_objects_port.search_by_synonym(
                    synonym=expert_name,
                    user_id=user_id
                )
            except Exception as e:
                logger.warning(
                    f"Error searching biological objects for synonym '{expert_name}': {str(e)}. "
                    "Entity will proceed to AI stage."
                )
                bio_objects = []

            matched_alternative: Optional[str] = None
            matched_obj: Optional[BiologicalObjectDomain] = None

            if bio_objects:
                # Take only the first element as specified by business requirements
                first_obj = bio_objects[0]

                # Build search set: all synonyms plus the official symbol
                candidates_in_db = {s.strip().upper() for s in first_obj.synonyms if s and s.strip()}
                if first_obj.symbol and first_obj.symbol.strip():
                    candidates_in_db.add(first_obj.symbol.strip().upper())

                # Check if any proposed alternative matches candidates in the DB object
                for alt in amb.alternative_ids:
                    alt_clean = alt.strip()
                    if alt_clean.upper() in candidates_in_db:
                        matched_alternative = alt_clean
                        matched_obj = first_obj
                        break

            if matched_alternative and matched_obj:
                # Build informative rationale including HGNC and UniProt identifiers if available
                id_tokens = []
                if matched_obj.hgnc_id and matched_obj.hgnc_id.strip():
                    id_tokens.append(f"HGNC: {matched_obj.hgnc_id.strip()}")
                if matched_obj.uniprot_id and matched_obj.uniprot_id.strip():
                    id_tokens.append(f"UniProt: {matched_obj.uniprot_id.strip()}")

                if id_tokens:
                    reason_str = f"Selected from BiopatternsG database ({', '.join(id_tokens)})"
                else:
                    reason_str = "Selected from BiopatternsG database"

                resolved_items.append(
                    AlignedItem(
                        current=expert_name,
                        aligned=matched_alternative,
                        status=AlignmentStatus.RESOLVED_BY_DATABASE,
                        reason=reason_str,
                        pubmed_ids=[]
                    )
                )
                processed.add(expert_name.upper())
            else:
                unresolved_ambiguous.append(amb)

        return resolved_items, unresolved_ambiguous, processed
