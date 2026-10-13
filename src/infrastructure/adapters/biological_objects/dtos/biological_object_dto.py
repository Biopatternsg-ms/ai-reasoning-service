from typing import List, Optional
from pydantic import BaseModel, Field
from src.domain.models.biological_object import BiologicalObjectDomain


class BiologicalObjectResponseDTO(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    symbol: Optional[str] = None
    hgnc_id: Optional[str] = Field(None, alias="hgncId")
    uniprot_id: Optional[str] = Field(None, alias="uniprotId")
    synonyms: List[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True

    def to_domain(self) -> BiologicalObjectDomain:
        return BiologicalObjectDomain(
            id=self.id,
            name=self.name,
            symbol=self.symbol,
            hgnc_id=self.hgnc_id,
            uniprot_id=self.uniprot_id,
            synonyms=self.synonyms or []
        )
