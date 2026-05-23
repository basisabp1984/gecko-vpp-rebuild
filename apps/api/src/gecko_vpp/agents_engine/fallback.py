"""Unknown-intent fallback handler."""

from __future__ import annotations

from typing import Any

from gecko_vpp.agents_engine.personas import PERSONAS, fallback_questions


def render_fallback(persona: str) -> str:
    cfg = PERSONAS.get(persona)
    samples = fallback_questions(persona)
    title = cfg["display_name"] if cfg else persona
    if not samples:
        return (
            f"Я — {title}. Я не зрозумів запит. Спробуйте перефразувати або "
            "запитайте про виробництво, ринок або батареї."
        )
    bullets = "\n".join(f"• {s}" for s in samples)
    return (
        f"Я — {title}. Я не зрозумів запит. Ось приклади того, що я можу:\n"
        f"{bullets}"
    )
