from typing import List, Optional
from pydantic import BaseModel, Field
from src.domain.models.alignment_proposal import AlignmentProposal
from src.domain.models.entity import AlignedItem as DomainAlignedItem


class AlignedItemDTO(BaseModel):
    current: str = Field(..., description="Original biomedical entity identifier")
    aligned: str = Field(..., description="Aligned canonical symbol (or fallback)")
    status: str = Field(..., description="Classification status: DIRECT_MATCH, RESOLVED_BY_AI, UNRESOLVED")
    reason: Optional[str] = Field(None, description="Biological rationale and applied criterion")

    @classmethod
    def from_domain(cls, item: DomainAlignedItem) -> "AlignedItemDTO":
        return cls(
            current=item.current,
            aligned=item.aligned,
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
            reason=item.reason or ""
        )


class AlignmentProposalResponseDTO(BaseModel):
    pipelineId: str = Field(..., description="Unique pipeline execution ID")
    objects: List[AlignedItemDTO] = Field(default_factory=list, description="List of aligned biological items")

    @classmethod
    def from_domain(cls, proposal: AlignmentProposal) -> "AlignmentProposalResponseDTO":
        return cls(
            pipelineId=proposal.pipeline_id,
            objects=[AlignedItemDTO.from_domain(obj) for obj in proposal.objects]
        )
