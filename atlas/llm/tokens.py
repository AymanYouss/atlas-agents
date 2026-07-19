"""Best-effort token estimation for budget accounting.

Uses tiktoken's ``cl100k_base`` as a provider-neutral proxy. Budgets are a safety
ceiling, not billing, so an approximate-but-cheap count is the right trade-off;
exact per-provider usage is still recorded from API responses where available.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _encoder():
    try:
        import tiktoken

        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    enc = _encoder()
    if enc is None:
        return max(1, len(text) // 4)  # ~4 chars/token fallback
    return len(enc.encode(text))
