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
import logging
from typing import List, Dict, Any

from src.domain.ports.pubmed_port import PubMedDataPort

logger = logging.getLogger(__name__)


class LiteratureEvidenceService:
    """
    Retrieves scientific knowledge base interaction events and publication abstracts
    from pubmed-integration for biomedical entities pending resolution.
    """

    def __init__(self, pubmed_port: PubMedDataPort):
        self.pubmed_port = pubmed_port

    async def fetch_literature_evidence(
        self,
        pipeline_id: str,
        entities: List[str],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieves knowledge base events and publication abstracts for unaligned entities.
        Includes all unique PubMed IDs associated with the term's events without truncation.
        """
        if not entities:
            return []

        literature_list: List[Dict[str, Any]] = []
        for term in entities:
            try:
                # 1. Fetch interaction events for this term
                events = await self.pubmed_port.get_kb_events_by_term(
                    pipeline_id=pipeline_id,
                    term=term,
                    user_id=user_id
                )

                # 2. Extract all unique PubMed IDs from events
                collected_pmids: List[str] = []
                event_summaries: List[str] = []
                for ev in events:
                    event_summaries.append(f"{ev.first} {ev.relation} {ev.second}")
                    for pmid in ev.pubmed_ids:
                        clean_pmid = pmid.strip()
                        if clean_pmid and clean_pmid not in collected_pmids:
                            collected_pmids.append(clean_pmid)

                # 3. Fetch all publications (titles and abstracts)
                pubs = []
                if collected_pmids:
                    pubs = await self.pubmed_port.get_publications_by_pmids(
                        pmids=collected_pmids,
                        user_id=user_id
                    )

                if pubs or event_summaries:
                    literature_list.append({
                        "symbol": term,
                        "events": event_summaries,
                        "publications": [
                            {
                                "pmid": p.pmid,
                                "title": p.title or "",
                                "abstractSnippet": p.text or ""
                            }
                            for p in pubs
                        ]
                    })
            except Exception as e:
                logger.warning(f"Could not retrieve literature evidence for term '{term}': {str(e)}")

        return literature_list
