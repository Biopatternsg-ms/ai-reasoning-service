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
from abc import ABC, abstractmethod
from src.domain.models.alignment_proposal import AlignmentProposal


class GenerateAlignmentProposalUseCase(ABC):
    """
    Driving / Inbound port contract for generating the biological entity
    alignment proposal for a given execution pipeline.
    """

    @abstractmethod
    async def execute(self, pipeline_id: str, user_id: str) -> AlignmentProposal:
        """
        Executes the alignment proposal generation pipeline:
        1. Retrieves pre-alignment data from pubmed-integration.
        2. Separates direct matches (zero tokens).
        3. Invokes LLM reasoning for ambiguous and unaligned terms.
        4. Applies safe fallbacks if LLM fails.
        5. Returns the consolidated AlignmentProposal domain aggregate.
        
        :param pipeline_id: Execution pipeline identifier.
        :param user_id: Authenticated user ID passed in x-user-id header.
        :return: Consolidated AlignmentProposal.
        """
        pass
