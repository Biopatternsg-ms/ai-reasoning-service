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
