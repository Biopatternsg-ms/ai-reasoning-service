from pydantic import BaseModel, Field
from typing import List


class AlignedAsDTO(BaseModel):
    expert_object_name: str = Field(alias="expertObjectName")
    alternative_ids: List[str] = Field(default_factory=list, alias="alternativeIds")

    class Config:
        populate_by_name = True


class AlignedResultDTO(BaseModel):
    pipeline_id: str = Field(alias="pipelineId")
    aligned: List[str] = Field(default_factory=list)
    no_aligned: List[str] = Field(default_factory=list, alias="noAligned")
    aligned_as: List[AlignedAsDTO] = Field(default_factory=list, alias="alignedAs")
    aligned_and_alternatives: List[str] = Field(default_factory=list, alias="alignedAndAlternatives")

    class Config:
        populate_by_name = True
