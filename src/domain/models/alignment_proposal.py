from typing import List
from pydantic import BaseModel, Field
from .entity import AlignedItem


class AlignmentProposal(BaseModel):
    pipeline_id: str = Field(..., description="Unique identifier of the execution pipeline")
    objects: List[AlignedItem] = Field(default_factory=list, description="List of processed biological entities")
