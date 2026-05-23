"""GECKO VPP agents engine — deterministic classifier + per-persona templates.

NO LLM. NO embeddings. Regex + lexicon + parameterised SQL.
Entry point: `agents_engine.runner.handle_query(...)`.
"""

from gecko_vpp.agents_engine.runner import handle_query

__all__ = ["handle_query"]
