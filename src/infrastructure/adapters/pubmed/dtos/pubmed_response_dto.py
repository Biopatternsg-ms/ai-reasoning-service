from typing import List
from pydantic import BaseModel, Field
from src.domain.models.pre_alignment import PipelinePreAlignmentData, AmbiguousEntityItem


class AlignedAsPubMedDTO(BaseModel):
    expert_object_name: str = Field(alias="expertObjectName")
    alternative_ids: List[str] = Field(default_factory=list, alias="alternativeIds")

    class Config:
        populate_by_name = True

    def to_domain(self) -> AmbiguousEntityItem:
        return AmbiguousEntityItem(
            expert_object_name=self.expert_object_name,
            alternative_ids=self.alternative_ids
        )


class AlignedResultPubMedDTO(BaseModel):
    pipeline_id: str = Field(alias="pipelineId")
    aligned: List[str] = Field(default_factory=list)
    no_aligned: List[str] = Field(default_factory=list, alias="noAligned")
    aligned_as: List[AlignedAsPubMedDTO] = Field(default_factory=list, alias="alignedAs")
    aligned_and_alternatives: List[str] = Field(default_factory=list, alias="alignedAndAlternatives")

    class Config:
        populate_by_name = True

    def to_domain(self) -> PipelinePreAlignmentData:
        return PipelinePreAlignmentData(
            pipeline_id=self.pipeline_id,
            aligned=self.aligned,
            no_aligned=self.no_aligned,
            aligned_as=[item.to_domain() for item in self.aligned_as]
        )
