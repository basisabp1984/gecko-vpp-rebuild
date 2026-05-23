"""Deterministic classifier.

`classify(question_uk, persona)` returns (intent_id, confidence, matched_pattern).

Mechanism:
1. Normalise text (`normalise.normalise`).
2. Iterate intent registry in descending priority. For each intent, test all
   its compiled patterns against the normalised string. First HIT wins.
3. If the matched intent is not in the persona's allowed list, demote to
   `unknown_intent`. (Spec §3.2.4)
4. If no pattern matches, return `unknown_intent` with confidence 0.0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from gecko_vpp.agents_engine.intents import INTENT_REGISTRY
from gecko_vpp.agents_engine.normalise import normalise
from gecko_vpp.agents_engine.personas import persona_allows


@dataclass(frozen=True)
class ClassifyResult:
    intent: str
    confidence: float
    matched_pattern: str
    normalised_text: str


# Sentinel for off-topic.
FALLBACK_INTENT = "unknown_intent"


def classify(question_uk: str, persona: str) -> ClassifyResult:
    """Classify a Ukrainian (or English-mix) question against the registry."""
    text = normalise(question_uk)
    if not text:
        return ClassifyResult(FALLBACK_INTENT, 0.0, "EMPTY", text)

    # Collect all (priority, confidence, intent_code, pattern) tuples,
    # iterate sorted descending. We re-compile here only once per cold
    # start — each intent module caches its compiled regex.
    candidates: list[tuple[int, float, str, re.Pattern[str]]] = []
    for intent_code, meta in INTENT_REGISTRY.items():
        for priority, conf, pat in meta["compiled_patterns"]:
            candidates.append((priority, conf, intent_code, pat))
    candidates.sort(key=lambda t: (-t[0], -t[1]))

    for _priority, conf, intent_code, pat in candidates:
        if pat.search(text):
            # Persona check — demote if not allowed.
            if not persona_allows(persona, intent_code):
                continue  # try next match — another intent might match AND be allowed
            return ClassifyResult(intent_code, conf, pat.pattern, text)

    return ClassifyResult(FALLBACK_INTENT, 0.0, "FALLBACK", text)
