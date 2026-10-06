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

    # Pre-alignment input:
    # - SST: already in aligned -> Stage 1
    # - SOS: in aligned_as with exact match ["SST", "XYLT2", "SOS"] -> Stage 1
    # - AML1: in aligned_as without exact match ["RUNX1", "CBFA2"] -> Stage 2 (requires AI)
    # - TATA: in no_aligned -> Stage 2 (requires AI + literature)
    mock_pubmed.get_aligned_results.return_value = PipelinePreAlignmentData(
        pipeline_id="test-pipeline",
        aligned=["SST"],
        no_aligned=["TATA"],
        aligned_as=[
            AmbiguousEntityItem(
                expert_object_name="SOS",
                alternative_ids=["SST", "XYLT2", "SOS"]
            ),
            AmbiguousEntityItem(
                expert_object_name="AML1",
                alternative_ids=["RUNX1", "CBFA2"]
            )
        ]
    )
    mock_pubmed.get_kb_events_by_term.return_value = []
    mock_pubmed.get_publications_by_pmids.return_value = []

    # LLM Mock response (only called for TATA and AML1)
    mock_llm.generate_json.return_value = {
        "resolutions": [
            {
                "current": "TATA",
                "aligned": "TBP",
                "criterion": "canonical_gene_mapping",
                "reason": "TATA-binding protein encoded by TBP gene"
            },
            {
                "current": "AML1",
                "aligned": "RUNX1",
                "criterion": "official_synonym",
                "reason": "RUNX1 is official canonical gene for historical alias AML1"
            }
        ]
    }

    use_case = GenerateAlignmentProposalUseCaseImpl(pubmed_port=mock_pubmed, llm_port=mock_llm)
    proposal = await use_case.execute(pipeline_id="test-pipeline", user_id="user-xyz")

    assert proposal.pipeline_id == "test-pipeline"
    assert len(proposal.objects) == 4

    # 1. Direct match from aligned (Stage 1)
    sst_item = next(o for o in proposal.objects if o.current == "SST")
    assert sst_item.aligned == "SST"
    assert sst_item.status == AlignmentStatus.DIRECT_MATCH

    # 2. Direct match found inside candidate synonyms (Stage 1 - ZERO tokens)
    sos_item = next(o for o in proposal.objects if o.current == "SOS")
    assert sos_item.aligned == "SOS"
    assert sos_item.status == AlignmentStatus.DIRECT_MATCH
    assert "Exact match found within candidate synonyms list" in sos_item.reason

    # 3. Resolved by AI (no_aligned) -> Stage 2
    tata_item = next(o for o in proposal.objects if o.current == "TATA")
    assert tata_item.aligned == "TBP"
    assert tata_item.status == AlignmentStatus.RESOLVED_BY_AI
    assert "[Criterion: canonical_gene_mapping]" in tata_item.reason

    # 4. Resolved by AI with justification (aligned_as without direct match) -> Stage 2
    aml1_item = next(o for o in proposal.objects if o.current == "AML1")
    assert aml1_item.aligned == "RUNX1"
    assert aml1_item.status == AlignmentStatus.RESOLVED_BY_AI
    assert "[Criterion: official_synonym]" in aml1_item.reason


@pytest.mark.asyncio
async def test_use_case_with_literature_evidence():
    from src.domain.models.evidence import KbEventDomain, PublicationEvidence

    mock_pubmed = AsyncMock()
    mock_llm = AsyncMock()

    mock_pubmed.get_aligned_results.return_value = PipelinePreAlignmentData(
        pipeline_id="pipe-lit-1",
        aligned=[],
        no_aligned=["TATA"],
        aligned_as=[]
    )
    mock_pubmed.get_kb_events_by_term.return_value = [
        KbEventDomain(first="TATA", relation="binds", second="DNA", pubmed_ids=["10523821"])
    ]
    mock_pubmed.get_publications_by_pmids.return_value = [
        PublicationEvidence(pmid="10523821", title="TBP structure", text="TATA-box binding protein (TBP) interacts with DNA.")
    ]

    mock_llm.generate_json.return_value = {
        "resolutions": [
            {
                "current": "TATA",
                "aligned": "TBP",
                "criterion": "canonical_gene_mapping",
                "reason": "PMID 10523821 confirms TATA corresponds to TBP",
                "pubmedIds": ["10523821"]
            }
        ]
    }

    use_case = GenerateAlignmentProposalUseCaseImpl(pubmed_port=mock_pubmed, llm_port=mock_llm)
    proposal = await use_case.execute(pipeline_id="pipe-lit-1", user_id="user-xyz")

    assert len(proposal.objects) == 1
    assert proposal.objects[0].current == "TATA"
    assert proposal.objects[0].aligned == "TBP"
    assert "PMID 10523821" in proposal.objects[0].reason
    assert proposal.objects[0].pubmed_ids == ["10523821"]
    mock_pubmed.get_kb_events_by_term.assert_called_once_with(pipeline_id="pipe-lit-1", term="TATA", user_id="user-xyz")
    mock_pubmed.get_publications_by_pmids.assert_called_once_with(pmids=["10523821"], user_id="user-xyz")


@pytest.mark.asyncio
async def test_use_case_with_pretrained_knowledge_no_pubmed_ids():
    mock_pubmed = AsyncMock()
    mock_llm = AsyncMock()

    mock_pubmed.get_aligned_results.return_value = PipelinePreAlignmentData(
        pipeline_id="pipe-pretrain-1",
        aligned=[],
        no_aligned=["MYOD"],
        aligned_as=[]
    )
    # No literature events found in pubmed-integration
    mock_pubmed.get_kb_events_by_term.return_value = []
    mock_pubmed.get_publications_by_pmids.return_value = []

    # LLM resolves via internal pre-trained biological knowledge
    mock_llm.generate_json.return_value = {
        "resolutions": [
            {
                "current": "MYOD",
                "aligned": "MYOD1",
                "criterion": "official_synonym",
                "reason": "Pre-trained knowledge: MYOD1 is the official HGNC canonical symbol for myogenic differentiation 1",
                "pubmedIds": []
            }
        ]
    }

    use_case = GenerateAlignmentProposalUseCaseImpl(pubmed_port=mock_pubmed, llm_port=mock_llm)
    proposal = await use_case.execute(pipeline_id="pipe-pretrain-1", user_id="user-xyz")

    assert len(proposal.objects) == 1
    item = proposal.objects[0]
    assert item.current == "MYOD"
    assert item.aligned == "MYOD1"
    assert item.status == AlignmentStatus.RESOLVED_BY_AI
    assert item.pubmed_ids == []
    assert "Pre-trained knowledge" in item.reason


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
