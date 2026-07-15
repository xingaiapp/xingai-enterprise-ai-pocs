"""Clause-level text chunks for the 3 policies in store.MOCK_POLICIES.

Per ADR-009 Phase 2: Policy Coverage's LLM path retrieves from this corpus
(via rag.py) instead of trusting a flat {covered: bool} dict — the point
is that a coverage determination and its adverse-action citation should
come from something that at least resembles reading the policy, not from
a pre-computed boolean. Still a POC fixture, not a real document store —
see POC README "Not Production Yet".
"""
from __future__ import annotations

from typing import Dict, List, TypedDict


class Chunk(TypedDict):
    clause_id: str
    title: str
    text: str


POLICY_DOCUMENTS: Dict[str, List[Chunk]] = {
    "POL-1001": [
        {
            "clause_id": "4.1",
            "title": "Grant of Coverage",
            "text": "We will pay for direct physical loss to the covered auto caused by collision with another object or by upset, subject to the limit and deductible shown on the declarations page.",
        },
        {
            "clause_id": "4.2(b)",
            "title": "Collision Coverage",
            "text": "Collision coverage applies to auto losses arising from impact with another vehicle or object, up to a limit of $15,000 per occurrence.",
        },
        {
            "clause_id": "5.1",
            "title": "Exclusions",
            "text": "This policy does not cover: wear and tear, mechanical breakdown, damage while the vehicle is used for racing or competitive driving, or damage occurring while the vehicle is being used to carry persons or property for a fee.",
        },
        {
            "clause_id": "5.4",
            "title": "Property Losses Excluded",
            "text": "This policy provides no coverage for losses to real property, dwellings, or personal property inside a residence; such losses require separate property coverage.",
        },
    ],
    "POL-1002": [
        {
            "clause_id": "3.1(a)",
            "title": "Dwelling Coverage",
            "text": "We will pay for direct physical loss to the dwelling described on the declarations page, up to a limit of $8,000 per occurrence, for covered perils including fire, windstorm, and water damage from a burst pipe.",
        },
        {
            "clause_id": "3.5",
            "title": "Exclusions",
            "text": "This policy does not cover flood, earth movement, or losses arising from neglect to protect the property after a loss.",
        },
        {
            "clause_id": "3.6",
            "title": "Vehicle Losses Excluded",
            "text": "This policy provides no coverage for losses to automobiles or other motor vehicles; such losses require separate auto coverage.",
        },
    ],
    "POL-1003": [
        {
            "clause_id": "4.2(b)",
            "title": "Collision Coverage",
            "text": "Collision coverage applies to auto losses arising from impact with another vehicle or object, up to a combined limit of $25,000 per occurrence shared with dwelling coverage below.",
        },
        {
            "clause_id": "3.1(a)",
            "title": "Dwelling Coverage",
            "text": "We will pay for direct physical loss to the dwelling described on the declarations page, up to a combined limit of $25,000 per occurrence shared with collision coverage above, for covered perils including fire, windstorm, and water damage from a burst pipe.",
        },
        {
            "clause_id": "5.1",
            "title": "Exclusions",
            "text": "This policy does not cover wear and tear, mechanical breakdown, flood, earth movement, or damage while the vehicle is used for racing or competitive driving.",
        },
    ],
}


def get_chunks(policy_id: str) -> List[Chunk]:
    return POLICY_DOCUMENTS.get(policy_id, [])
