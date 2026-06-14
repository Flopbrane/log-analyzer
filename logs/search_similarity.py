# -*- coding: utf-8 -*-
"""API Keyなしで動く近似検索用の軽量ベクトル化モジュール。"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, cast

from openai import OpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

DEFAULT_SIMILARITY_THRESHOLD = 0.08
SIMILARITY_CACHE_KIND = "tfidf_char_ngram_v1"
CACHE_PATH: Path = Path(__file__).with_name("_cash.jsonl")

TOKEN_PATTERN: re.Pattern[str] = re.compile(r"[a-z0-9]+")

QUERY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "gpu": ("gpu", "graphics", "video", "vram"),
    "memory": ("memory", "mem", "ram", "vram", "mb", "used", "usage"),
    "pressure": ("pressure", "high", "used", "usage", "percent", "limit", "total"),
    "reboot": ("reboot", "restart", "boot", "startup"),
    "restart": ("restart", "reboot", "boot"),
    "clock": ("clock", "time", "timestamp"),
    "jump": ("jump", "drift", "diff", "gap", "change"),
    "symptom": ("symptom", "warning", "error", "detected", "invalid"),
    "symptoms": ("symptom", "warning", "error", "detected", "invalid"),
}

_cache: dict[str, Counter[str]] | None = None


def _normalize(text: str) -> str:
    return text.lower().replace("_", " ")


def _text_hash(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


def _iter_char_ngrams(text: str) -> list[str]:
    compact: str = re.sub(r"\s+", " ", _normalize(text)).strip()
    grams: list[str] = []
    for ngram_size in (3, 4, 5):
        if len(compact) < ngram_size:
            continue
        grams.extend(
            f"c{ngram_size}:{compact[index:index + ngram_size]}"
            for index in range(len(compact) - ngram_size + 1)
        )
    return grams


def _iter_word_features(text: str, *, expand_query: bool) -> list[str]:
    tokens: list[str] = TOKEN_PATTERN.findall(_normalize(text))
    features: list[str] = []

    for token in tokens:
        features.extend([f"w:{token}"] * 3)
        if expand_query:
            for synonym in QUERY_SYNONYMS.get(token, ()):
                features.extend([f"w:{synonym}"] * 2)

    features.extend(f"b:{left}_{right}" for left, right in zip(tokens, tokens[1:]))
    return features


def vectorize_text(text: str, *, expand_query: bool = False) -> Counter[str]:
    """文字n-gramと単語特徴を混ぜた軽量ベクトルを作る。"""
    vector: Counter[str] = Counter()
    vector.update(_iter_char_ngrams(text))
    vector.update(_iter_word_features(text, expand_query=expand_query))
    return vector


def _load_cache() -> dict[str, Counter[str]]:
    global _cache  # noqa: PLW0603
    if _cache is not None:
        return _cache

    cache: dict[str, Counter[str]] = {}
    if CACHE_PATH.exists():
        for line in CACHE_PATH.read_text(encoding="utf-8").splitlines():
            try:
                record: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("kind") != SIMILARITY_CACHE_KIND:
                continue
            text_hash: object = record.get("hash")
            raw_vector: object = record.get("vector")
            if isinstance(text_hash, str) and isinstance(raw_vector, dict):
                vector_items: dict[str, Any] = cast(dict[str, Any], raw_vector)

                normalized: dict[str, int] = {}

                for key, value in vector_items.items():
                    if isinstance(value, (int, float)):
                        normalized[str(key)] = int(value)

                cache[text_hash] = Counter(normalized)

    _cache = cache
    return _cache


def _append_cache(text_hash: str, vector: Counter[str]) -> None:
    record: dict[str, object] = {
        "kind": SIMILARITY_CACHE_KIND,
        "hash": text_hash,
        "vector": dict(vector),
    }
    with CACHE_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def cached_document_vector(text: str) -> Counter[str]:
    """ログ本文側のベクトルを _cash.jsonl にキャッシュして返す。"""
    cache: dict[str, Counter[str]] = _load_cache()
    text_hash: str = _text_hash(text)
    if text_hash in cache:
        return cache[text_hash]

    vector: Counter[str] = vectorize_text(text)
    cache[text_hash] = vector
    _append_cache(text_hash, vector)
    return vector


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0

    if len(left) > len(right):
        left, right = right, left

    dot: float = sum(weight * right.get(feature, 0) for feature, weight in left.items())
    left_norm: float = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm: float = math.sqrt(sum(weight * weight for weight in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def similarity_score(query_text: str, document_text: str) -> float:
    """検索語とログ本文の近さを0.0-1.0で返す。"""
    query_vector: Counter[str] = vectorize_text(query_text, expand_query=True)
    document_vector: Counter[str] = cached_document_vector(document_text)
    return cosine_similarity(query_vector, document_vector)


# Future OpenAI embeddings hook (requires OPENAI_API_KEY and paid API access):

def embedding_vector(text: str) -> list[float]:
    """OpenAIの埋め込みAPIを使ってテキストをベクトル化する。"""
    client = OpenAI()
    response: CreateEmbeddingResponse = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


__all__: list[str] = [
    "similarity_score",
    "embedding_vector",
]
