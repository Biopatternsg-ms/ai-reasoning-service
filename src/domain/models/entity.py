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
