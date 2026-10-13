from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class AlignmentStatus(str, Enum):
    DIRECT_MATCH = "DIRECT_MATCH"
    RESOLVED_BY_DATABASE = "RESOLVED_BY_DATABASE"
    RESOLVED_BY_AI = "RESOLVED_BY_AI"
    UNRESOLVED = "UNRESOLVED"


class AlignedItem(BaseModel):
    current: str = Field(..., description="Original biomedical entity identifier or name in the user study")
    aligned: str = Field(..., description="Aligned canonical symbol (or fallback)")
    status: AlignmentStatus = Field(..., description="Classification status: DIRECT_MATCH, RESOLVED_BY_AI, or UNRESOLVED")
    reason: Optional[str] = Field(None, description="Human-readable biological justification and criterion applied")
    pubmed_ids: List[str] = Field(default_factory=list, description="List of supporting PubMed IDs, if evidenced in publications")
