import pytest
from src.domain.models.entity import AlignmentStatus, AlignedItem
from src.domain.models.alignment_proposal import AlignmentProposal
from src.domain.models.pre_alignment import PipelinePreAlignmentData, AmbiguousEntityItem


def test_aligned_item_creation():
    item = AlignedItem(
        current="SST",
        aligned="SST",
        status=AlignmentStatus.DIRECT_MATCH,
        reason="Direct match"
    )
    assert item.current == "SST"
    assert item.aligned == "SST"
    assert item.status == AlignmentStatus.DIRECT_MATCH
    assert item.reason == "Direct match"


def test_alignment_proposal_creation():
    item1 = AlignedItem(current="SST", aligned="SST", status=AlignmentStatus.DIRECT_MATCH)
    item2 = AlignedItem(current="TATA", aligned="TBP", status=AlignmentStatus.RESOLVED_BY_AI, reason="Gene mapping")

    proposal = AlignmentProposal(
        pipeline_id="pipe-123",
        objects=[item1, item2]
    )
    assert proposal.pipeline_id == "pipe-123"
    assert len(proposal.objects) == 2
    assert proposal.objects[1].aligned == "TBP"


def test_pre_alignment_data_creation():
    data = PipelinePreAlignmentData(
        pipeline_id="test-pipe",
        aligned=["SST"],
        no_aligned=["TATA"],
        aligned_as=[AmbiguousEntityItem(expert_object_name="SOS", alternative_ids=["SOS", "XYLT2"])]
    )
    assert data.pipeline_id == "test-pipe"
    assert len(data.aligned_as) == 1
    assert data.aligned_as[0].expert_object_name == "SOS"
