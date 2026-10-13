#
# Copyright © 2026 biopatternsg (biopatternsg@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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
