"""Text normalisation for the agents classifier.

Pure stdlib: casefold + NFKD diacritic strip + stopword removal.
Used by `classifier.classify()`.
"""

from __future__ import annotations

import re
import unicodedata

# Tiny Ukrainian stopword set — keep it short so we don't accidentally
# strip a token that turns out to be a discriminator for some intent.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "та", "і", "й", "або", "з", "із", "по", "на", "в", "у", "до",
        "для", "чи", "як", "що", "це", "той", "ця", "ці", "цей",
        "а", "але", "не", "ні", "є", "був", "була", "було",
        "the", "a", "an", "of", "to", "and", "or", "in", "on",
    }
)

_TOKEN_SPLIT = re.compile(r"[\s\-,?!.:;()\"'’`/\\]+")


def normalise(text: str) -> str:
    """Lowercase + strip diacritics + drop stopwords. Returns a space-joined
    string of tokens, ready for regex matching.
    """
    if not text:
        return ""
    # Unicode normalise — DON'T strip Cyrillic combining accents (rare in UA
    # anyway). We only normalise width/compatibility forms.
    t = unicodedata.normalize("NFKC", text)
    t = t.casefold()
    # Replace ё → е (sometimes shows up via copy-paste); і/ї/є keep as-is.
    t = t.replace("ё", "е").replace("ъ", "")
    tokens = [tok for tok in _TOKEN_SPLIT.split(t) if tok and tok not in _STOPWORDS]
    return " ".join(tokens)
