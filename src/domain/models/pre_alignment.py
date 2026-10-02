from typing import List
from pydantic import BaseModel, Field


class AmbiguousEntityItem(BaseModel):
    expert_object_name: str = Field(..., description="Original ambiguous entity symbol")
    alternative_ids: List[str] = Field(default_factory=list, description="Candidate IDs identified by PubMed")


class PipelinePreAlignmentData(BaseModel):
    pipeline_id: str
    aligned: List[str] = Field(default_factory=list, description="Direct matches already recognized")
    no_aligned: List[str] = Field(default_factory=list, description="Entities without initial match")
    aligned_as: List[AmbiguousEntityItem] = Field(default_factory=list, description="Entities with multiple candidates")
