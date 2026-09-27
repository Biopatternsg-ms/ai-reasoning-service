import pytest
from unittest.mock import AsyncMock
from src.services.alignment_service import AlignmentService
from src.models.pubmed_dto import AlignedResultDTO, AlignedAsDTO


@pytest.mark.asyncio
async def test_alignment_service_success():
    # Mock pubmed-integration response
    mock_pubmed_data = AlignedResultDTO(
        pipelineId="pipeline-test-123",
        aligned=["EGF", "SST"],
        noAligned=["TATA", "LANREOTIDE"],
        alignedAs=[
            AlignedAsDTO(
                expertObjectName="SOS",
                alternativeIds=["SST", "SOS", "XYLT2"]
            )
        ],
        alignedAndAlternatives=["EGF", "SST", "SOS", "XYLT2"]
    )

    mock_pubmed_client = AsyncMock()
    mock_pubmed_client.get_aligned_results.return_value = mock_pubmed_data

    # Mock LLM Gateway response
    mock_llm_gateway = AsyncMock()
    mock_llm_gateway.generate_json.return_value = {
        "resolutions": [
            {
                "current": "TATA",
                "aligned": "TBP",
                "criterion": "canonical_gene_mapping",
                "reason": "TATA-binding protein (TBP gene)"
            },
            {
                "current": "LANREOTIDE",
                "aligned": "OCTREOTIDE",
                "criterion": "functional_analog",
                "reason": "Somatostatin synthetic analog equivalence"
            },
            {
                "current": "SOS",
                "aligned": "SOS",
                "criterion": "identity",
                "reason": "Canonical guanine nucleotide exchange factor"
            }
        ]
    }

    service = AlignmentService(
        pubmed_client=mock_pubmed_client,
        llm_gateway=mock_llm_gateway
    )

    result = await service.generate_alignment_proposal("pipeline-test-123", user_id="user-test-789")

    mock_pubmed_client.get_aligned_results.assert_awaited_once_with("pipeline-test-123", user_id="user-test-789")

    assert result.pipelineId == "pipeline-test-123"
    assert len(result.objects) == 5

    objects_by_current = {obj.current: obj for obj in result.objects}

    # Verify direct matches
    assert objects_by_current["EGF"].aligned == "EGF"
    assert objects_by_current["EGF"].status == "DIRECT_MATCH"

    assert objects_by_current["SST"].aligned == "SST"
    assert objects_by_current["SST"].status == "DIRECT_MATCH"

    # Verify AI resolutions
    assert objects_by_current["TATA"].aligned == "TBP"
    assert objects_by_current["TATA"].status == "RESOLVED_BY_AI"
    assert "TBP" in objects_by_current["TATA"].reason
    assert "canonical_gene_mapping" in objects_by_current["TATA"].reason

    assert objects_by_current["LANREOTIDE"].aligned == "OCTREOTIDE"
    assert objects_by_current["LANREOTIDE"].status == "RESOLVED_BY_AI"

    assert objects_by_current["SOS"].aligned == "SOS"
    assert objects_by_current["SOS"].status == "RESOLVED_BY_AI"


@pytest.mark.asyncio
async def test_alignment_service_llm_fallback():
    # When the LLM fails, the service gracefully degrades without crashing
    mock_pubmed_data = AlignedResultDTO(
        pipelineId="pipeline-test-fallback",
        aligned=["EGF"],
        noAligned=["UNKNOWN_ENTITY"],
        alignedAs=[
            AlignedAsDTO(
                expertObjectName="AMBIGUOUS",
                alternativeIds=["CANDIDATE_A", "CANDIDATE_B"]
            )
        ],
        alignedAndAlternatives=["EGF", "CANDIDATE_A"]
    )

    mock_pubmed_client = AsyncMock()
    mock_pubmed_client.get_aligned_results.return_value = mock_pubmed_data

    # Simulate LLM failure (e.g., timeout or invalid API key)
    mock_llm_gateway = AsyncMock()
    mock_llm_gateway.generate_json.side_effect = Exception("Connection lost with LLM")

    service = AlignmentService(
        pubmed_client=mock_pubmed_client,
        llm_gateway=mock_llm_gateway
    )

    result = await service.generate_alignment_proposal("pipeline-test-fallback", user_id="user-fallback-123")

    mock_pubmed_client.get_aligned_results.assert_awaited_once_with("pipeline-test-fallback", user_id="user-fallback-123")

    assert result.pipelineId == "pipeline-test-fallback"
    assert len(result.objects) == 3

    objects_by_current = {obj.current: obj for obj in result.objects}

    # Direct match is preserved
    assert objects_by_current["EGF"].status == "DIRECT_MATCH"

    # Unresolved fallbacks are preserved without throwing exceptions to the user
    assert objects_by_current["UNKNOWN_ENTITY"].aligned == "UNKNOWN_ENTITY"
    assert objects_by_current["UNKNOWN_ENTITY"].status == "UNRESOLVED"

    assert objects_by_current["AMBIGUOUS"].status == "UNRESOLVED"
    assert objects_by_current["AMBIGUOUS"].aligned == "CANDIDATE_A"


def test_process_direct_matches():
    service = AlignmentService()
    items, processed = service._process_direct_matches(["SST", "EGF"])
    assert len(items) == 2
    assert processed == {"SST", "EGF"}
    assert items[0].status == "DIRECT_MATCH"
    assert items[0].current == "SST"
    assert items[0].aligned == "SST"


def test_filter_pending_entities():
    service = AlignmentService()
    pubmed_data = AlignedResultDTO(
        pipelineId="p1",
        aligned=["SST"],
        noAligned=["TATA", "SST"],  # SST already processed
        alignedAs=[
            AlignedAsDTO(expertObjectName="SST", alternativeIds=["SST_1"]),  # Already processed
            AlignedAsDTO(expertObjectName="SOS", alternativeIds=["SOS_1"])
        ],
        alignedAndAlternatives=[]
    )
    entities, ambiguous = service._filter_pending_entities(pubmed_data, processed_symbols={"SST"})
    assert entities == ["TATA"]
    assert len(ambiguous) == 1
    assert ambiguous[0].expert_object_name == "SOS"


def test_map_unaligned_entities():
    service = AlignmentService()
    resolutions = {"TATA": {"aligned": "TBP", "reason": "TATA box protein"}}
    items = service._map_unaligned_entities(["TATA", "UNKNOWN"], resolutions)

    assert len(items) == 2
    assert items[0].aligned == "TBP"
    assert items[0].status == "RESOLVED_BY_AI"

    assert items[1].aligned == "UNKNOWN"
    assert items[1].status == "UNRESOLVED"


def test_map_ambiguous_entities():
    service = AlignmentService()
    ambiguous = [
        AlignedAsDTO(expertObjectName="SOS", alternativeIds=["SOS", "OTHER"]),
        AlignedAsDTO(expertObjectName="FALLBACK", alternativeIds=["ALT_1", "ALT_2"])
    ]
    resolutions = {"SOS": {"aligned": "SOS", "reason": "Guanine factor"}}
    items = service._map_ambiguous_entities(ambiguous, resolutions)

    assert len(items) == 2
    assert items[0].aligned == "SOS"
    assert items[0].status == "RESOLVED_BY_AI"

    # Unresolved takes the first candidate
    assert items[1].aligned == "ALT_1"
    assert items[1].status == "UNRESOLVED"
