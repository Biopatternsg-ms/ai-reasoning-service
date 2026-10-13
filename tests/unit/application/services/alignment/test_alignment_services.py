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
import pytest
from unittest.mock import AsyncMock

from src.application.services.alignment import (
    DirectMatchingService,
    DatabaseMatchingService,
    LiteratureEvidenceService,
    AIResolutionService,
)
from src.domain.models.pre_alignment import PipelinePreAlignmentData, AmbiguousEntityItem
from src.domain.models.entity import AlignmentStatus
from src.domain.models.biological_object import BiologicalObjectDomain
from src.domain.models.evidence import KbEventDomain, PublicationEvidence


def test_direct_matching_service():
    service = DirectMatchingService()
    pre_data = PipelinePreAlignmentData(
        pipeline_id="pipe-1",
        aligned=["SST"],
        no_aligned=["TATA"],
        aligned_as=[
            AmbiguousEntityItem(expert_object_name="SOS", alternative_ids=["XYLT2", "SOS"]),
            AmbiguousEntityItem(expert_object_name="AML1", alternative_ids=["RUNX1", "CBFA2"])
        ]
    )

    direct_items, pending_ambiguous, processed = service.process_direct_matches(pre_data)

    assert len(direct_items) == 2  # SST (from aligned) and SOS (exact match in alternative_ids)
    assert len(pending_ambiguous) == 1
    assert pending_ambiguous[0].expert_object_name == "AML1"
    assert "SST" in processed
    assert "SOS" in processed


@pytest.mark.asyncio
async def test_database_matching_service():
    mock_bio_port = AsyncMock()
    mock_bio_port.search_by_synonym.return_value = [
        BiologicalObjectDomain(
            id="obj-1",
            symbol="RUNX1",
            name="Runt-related transcription factor 1",
            hgnc_id="10471",
            uniprot_id="Q01196",
            synonyms=["AML1", "CBFA2"]
        )
    ]

    service = DatabaseMatchingService(biological_objects_port=mock_bio_port)
    ambiguous_input = [
        AmbiguousEntityItem(expert_object_name="AML1", alternative_ids=["RUNX1", "CBFA2"])
    ]

    resolved_items, unresolved, processed = await service.process_database_matches(
        ambiguous_entities=ambiguous_input,
        user_id="user-1"
    )

    assert len(resolved_items) == 1
    assert resolved_items[0].current == "AML1"
    assert resolved_items[0].aligned == "RUNX1"
    assert resolved_items[0].status == AlignmentStatus.RESOLVED_BY_DATABASE
    assert "HGNC: 10471" in resolved_items[0].reason
    assert "UniProt: Q01196" in resolved_items[0].reason
    assert len(unresolved) == 0
    assert "AML1" in processed


@pytest.mark.asyncio
async def test_literature_evidence_service():
    mock_pubmed_port = AsyncMock()
    mock_pubmed_port.get_kb_events_by_term.return_value = [
        KbEventDomain(first="TATA", relation="binds", second="TBP", pubmed_ids=["12345"])
    ]
    mock_pubmed_port.get_publications_by_pmids.return_value = [
        PublicationEvidence(pmid="12345", title="TATA binding study", text="Detailed abstract text")
    ]

    service = LiteratureEvidenceService(pubmed_port=mock_pubmed_port)
    evidence = await service.fetch_literature_evidence(
        pipeline_id="pipe-1",
        entities=["TATA"],
        user_id="user-1"
    )

    assert len(evidence) == 1
    assert evidence[0]["symbol"] == "TATA"
    assert len(evidence[0]["events"]) == 1
    assert evidence[0]["publications"][0]["pmid"] == "12345"


@pytest.mark.asyncio
async def test_ai_resolution_service():
    mock_llm_port = AsyncMock()
    mock_llm_port.generate_json.return_value = {
        "resolutions": [
            {
                "current": "TATA",
                "aligned": "TBP",
                "status": "RESOLVED_BY_AI",
                "reason": "TATA-binding protein canonical mapping",
                "criterion": "canonical_gene_mapping",
                "pubmedIds": ["12345"]
            }
        ]
    }

    service = AIResolutionService(llm_port=mock_llm_port)
    unaligned_items, ambiguous_items = await service.resolve_entities(
        entities_to_resolve=["TATA"],
        ambiguous_to_resolve=[],
        literature_evidence=[]
    )

    assert len(unaligned_items) == 1
    assert unaligned_items[0].current == "TATA"
    assert unaligned_items[0].aligned == "TBP"
    assert unaligned_items[0].status == AlignmentStatus.RESOLVED_BY_AI
    assert unaligned_items[0].pubmed_ids == ["12345"]
    assert "[Criterion: canonical_gene_mapping]" in unaligned_items[0].reason
    assert len(ambiguous_items) == 0
