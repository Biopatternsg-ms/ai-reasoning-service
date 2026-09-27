from pydantic import BaseModel
from typing import List


class AlignedItem(BaseModel):
    current: str
    aligned: str
    status: str  # "DIRECT_MATCH", "RESOLVED_BY_AI", "UNRESOLVED"
    reason: str


class AlignmentProposalResponse(BaseModel):
    pipelineId: str
    objects: List[AlignedItem]
