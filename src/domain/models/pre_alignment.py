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
from typing import List
from pydantic import BaseModel, Field


class AmbiguousEntityItem(BaseModel):
    expert_object_name: str = Field(..., description="Original ambiguous entity symbol")
    alternative_ids: List[str] = Field(default_factory=list, description="Candidate IDs identified by PubMed")


class PipelinePreAlignmentData(BaseModel):
    pipeline_id: str
    aligned: List[str] = Field(default_factory=list, description="Direct matches already recognized")
    no_aligned: List[str] = Field(default_factory=list, description="Entities without initial match")
    aligned_as: List[AmbiguousEntityItem] = Field(default_factory=list, description="Entities with multiple candidates")
