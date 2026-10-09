from typing import List, Optional
from pydantic import BaseModel, Field


class BiologicalObjectDomain(BaseModel):
    """
    Domain entity representing a biological object retrieved from the BiopatternsG knowledge base.
    """
    id: Optional[str] = Field(None, description="Database unique identifier")
    name: Optional[str] = Field(None, description="Full descriptive biological name")
    symbol: Optional[str] = Field(None, description="Official gene/protein symbol")
    hgnc_id: Optional[str] = Field(None, description="HGNC identifier (e.g. HGNC:10456)")
    uniprot_id: Optional[str] = Field(None, description="UniProt accession identifier")
    synonyms: List[str] = Field(default_factory=list, description="Associated synonyms and aliases")
