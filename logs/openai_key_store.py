# -*- coding: utf-8 -*-
"""OpenAI API KeyをScriptへ直書きせずOS資格情報ストアで扱う。"""
from __future__ import annotations

from typing import Any

from openai import OpenAI  # type: ignore[import-not-found]

SERVICE_NAME = "logger_project_openai"
ACCOUNT_NAME = "OPENAI_API_KEY"


def _load_keyring() -> None | Any:
    try:
        import keyring  # type: ignore[import-not-found]
    except ImportError:
        return None
    return keyring


def is_keyring_available() -> bool:
    """keyringが利用可能ならTrue。"""
    return _load_keyring() is not None


def create_openai_client() -> OpenAI:
    api_key: str | None = get_openai_api_key()

    if not api_key:
        raise RuntimeError("OpenAI API Key not found")

    try:
        return OpenAI(api_key=api_key)
    finally:
        api_key = None


def get_openai_api_key() -> str | None:
    """保存済みAPI Keyを取得する。未登録ならNone。"""
    keyring = _load_keyring()
    if keyring is None:
        return None
    key: str | None = keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)
    return key or None


def has_openai_api_key() -> bool:
    """保存済みAPI Keyがあるか確認する。"""
    return get_openai_api_key() is not None


def save_openai_api_key(api_key: str) -> None:
    """API KeyをOS資格情報ストアへ保存する。"""
    keyring = _load_keyring()
    if keyring is None:
        raise RuntimeError("keyring module is not installed")
    keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, api_key)


def delete_openai_api_key() -> None:
    """保存済みAPI Keyを削除する。"""
    keyring = _load_keyring()
    if keyring is None:
        raise RuntimeError("keyring module is not installed")
    try:
        keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
    except keyring.errors.PasswordDeleteError:
        return
