import pytest
from unittest.mock import AsyncMock

from src.application.use_cases.impl.alignment_use_case_impl import GenerateAlignmentProposalUseCaseImpl
from src.domain.models.pre_alignment import PipelinePreAlignmentData, AmbiguousEntityItem
from src.domain.models.entity import AlignmentStatus
from src.domain.exceptions.exceptions import EntityValidationException


@pytest.mark.asyncio
async def test_use_case_validation():
    mock_pubmed = AsyncMock()
    mock_llm = AsyncMock()
    use_case = GenerateAlignmentProposalUseCaseImpl(pubmed_port=mock_pubmed, llm_port=mock_llm)

    with pytest.raises(EntityValidationException):
        await use_case.execute(pipeline_id="", user_id="user1")

    with pytest.raises(EntityValidationException):
        await use_case.execute(pipeline_id="pipe1", user_id="")


@pytest.mark.asyncio
async def test_use_case_execution_with_llm_and_direct_matches():
    mock_pubmed = AsyncMock()
    mock_llm = AsyncMock()

    # Pre-alignment input
    mock_pubmed.get_aligned_results.return_value = PipelinePreAlignmentData(
        pipeline_id="test-pipeline",
        aligned=["SST"],
        no_aligned=["TATA"],
        aligned_as=[
            AmbiguousEntityItem(
                expert_object_name="SOS",
                alternative_ids=["SST", "XYLT2", "SOS"]
            )
        ]
    )

    # LLM Mock response
    mock_llm.generate_json.return_value = {
        "resolutions": [
            {
                "current": "TATA",
                "aligned": "TBP",
                "criterion": "canonical_gene_mapping",
                "reason": "TATA-binding protein encoded by TBP gene"
            },
            {
                "current": "SOS",
                "aligned": "SOS",
                "criterion": "identity",
                "reason": "Son of Sevenless guanine nucleotide exchange factor"
            }
        ]
    }

    use_case = GenerateAlignmentProposalUseCaseImpl(pubmed_port=mock_pubmed, llm_port=mock_llm)
    proposal = await use_case.execute(pipeline_id="test-pipeline", user_id="user-xyz")

    assert proposal.pipeline_id == "test-pipeline"
    assert len(proposal.objects) == 3

    # 1. Direct match
    sst_item = next(o for o in proposal.objects if o.current == "SST")
    assert sst_item.aligned == "SST"
    assert sst_item.status == AlignmentStatus.DIRECT_MATCH

    # 2. Resolved by AI (no_aligned)
    tata_item = next(o for o in proposal.objects if o.current == "TATA")
    assert tata_item.aligned == "TBP"
    assert tata_item.status == AlignmentStatus.RESOLVED_BY_AI
    assert "[Criterion: canonical_gene_mapping]" in tata_item.reason

    # 3. Resolved by AI (aligned_as)
    sos_item = next(o for o in proposal.objects if o.current == "SOS")
    assert sos_item.aligned == "SOS"
    assert sos_item.status == AlignmentStatus.RESOLVED_BY_AI
    assert "[Criterion: identity]" in sos_item.reason


@pytest.mark.asyncio
async def test_use_case_fallback_when_llm_fails():
    mock_pubmed = AsyncMock()
    mock_llm = AsyncMock()

    mock_pubmed.get_aligned_results.return_value = PipelinePreAlignmentData(
        pipeline_id="test-pipeline-fallback",
        aligned=[],
        no_aligned=["UNKNOWN_XYZ"],
        aligned_as=[
            AmbiguousEntityItem(
                expert_object_name="AMBIG_GENE",
                alternative_ids=["CANDIDATE_1", "CANDIDATE_2"]
            )
        ]
    )

    # LLM throws an exception (e.g. timeout / network error)
    mock_llm.generate_json.side_effect = Exception("LLM connection timeout")

    use_case = GenerateAlignmentProposalUseCaseImpl(pubmed_port=mock_pubmed, llm_port=mock_llm)
    proposal = await use_case.execute(pipeline_id="test-pipeline-fallback", user_id="user-xyz")

    assert proposal.pipeline_id == "test-pipeline-fallback"
    assert len(proposal.objects) == 2

    # Unaligned fallback
    unaligned_item = next(o for o in proposal.objects if o.current == "UNKNOWN_XYZ")
    assert unaligned_item.aligned == "UNKNOWN_XYZ"
    assert unaligned_item.status == AlignmentStatus.UNRESOLVED

    # Ambiguous fallback
    ambig_item = next(o for o in proposal.objects if o.current == "AMBIG_GENE")
    assert ambig_item.aligned == "CANDIDATE_1"
    assert ambig_item.status == AlignmentStatus.UNRESOLVED
