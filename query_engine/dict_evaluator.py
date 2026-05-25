"""旧APIを残すための互換モジュール。

新しいコードでは query_engine.evaluators.memory を使ってください。
"""
from __future__ import annotations

from query_engine.evaluators.memory import match_node, match_query, search

__all__ = ["match_node", "match_query", "search"]
