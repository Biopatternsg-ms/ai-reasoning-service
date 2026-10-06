from typing import List, Optional
from pydantic import BaseModel, Field


class KbEventDomain(BaseModel):
    first: str = Field(..., description="Subject biological entity")
    relation: str = Field(..., description="Biological interaction / relationship")
    second: str = Field(..., description="Object biological entity")
    pubmed_ids: List[str] = Field(default_factory=list, description="List of supporting PubMed IDs")


class PublicationEvidence(BaseModel):
    pmid: str = Field(..., description="PubMed identifier")
    title: Optional[str] = Field(None, description="Article title")
    text: Optional[str] = Field(None, description="Abstract / full publication text")


class EntityLiteratureEvidence(BaseModel):
    term: str = Field(..., description="Unresolved or candidate entity symbol")
    events: List[KbEventDomain] = Field(default_factory=list, description="Knowledge base interactions")
    publications: List[PublicationEvidence] = Field(default_factory=list, description="Retrieved publication abstracts")
