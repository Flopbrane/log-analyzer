# -*- coding: utf-8 -*-
"""Defender調査JSONLの判定ルール。"""
from __future__ import annotations

from enum import StrEnum


class DefenderClassification(StrEnum):
    """Defender triage 用の分類。"""

    ALERT = "alert"
    WATCH = "watch"
    ALLOW = "allow"
    INFO = "info"


KNOWN_SIGNERS: frozenset[str] = frozenset(
    {
        "microsoft",
        "zoom communications",
        "google",
        "intel",
        "nvidia",
        "adobe",
        "axosoft",
        "discord",
        "logitech",
        "blackmagic design",
    }
)

KNOWN_PATH_HINTS: tuple[str, ...] = (
    r"\program files",
    r"\microsoft\windows defender",
    r"\zoom\bin",
    r"\discord",
    r"\onedrive",
    r"\adobe",
    "\\google\\",
    r"\nvidia",
    r"\intel",
    r"\gitkraken",
    r"\python312\scripts",
)

KNOWN_FILENAMES: frozenset[str] = frozenset(
    {
        "update.exe",
        "zupdater.exe",
        "git.exe",
        "powertoys.update.exe",
        "onedrive.exe",
        "adobearm.exe",
    }
)

ALERT_PATH_HINTS: tuple[str, ...] = (
    "\\cam_f\\1\\",
    "disableantispyware",
)


def classify_executable(
    *,
    full_name: str,
    signature: str,
    signer: str,
) -> DefenderClassification:
    lowered_path = full_name.lower()
    lowered_signature = signature.lower()
    lowered_signer = signer.lower()
    file_name = lowered_path.rsplit("\\", 1)[-1]

    if _contains_any(lowered_path, ALERT_PATH_HINTS):
        return DefenderClassification.ALERT

    if lowered_signature == "valid" and (
        _contains_any(lowered_signer, tuple(KNOWN_SIGNERS))
        or _contains_any(lowered_path, KNOWN_PATH_HINTS)
        or file_name in KNOWN_FILENAMES
    ):
        return DefenderClassification.ALLOW

    if lowered_signature and lowered_signature != "valid":
        return DefenderClassification.WATCH

    if r"\appdata\roaming" in lowered_path or r"\programdata" in lowered_path:
        return DefenderClassification.WATCH

    return DefenderClassification.INFO


def classify_path(path_text: str) -> DefenderClassification:
    lowered = path_text.lower()
    file_name = lowered.rsplit("\\", 1)[-1]

    if _contains_any(lowered, ALERT_PATH_HINTS):
        return DefenderClassification.ALERT

    if _contains_any(lowered, KNOWN_PATH_HINTS) or file_name in KNOWN_FILENAMES:
        return DefenderClassification.ALLOW

    if ".exe" in lowered:
        return DefenderClassification.WATCH

    return DefenderClassification.INFO


def classification_to_level(classification: DefenderClassification) -> str:
    return {
        DefenderClassification.ALERT: "CRITICAL",
        DefenderClassification.WATCH: "WARNING",
        DefenderClassification.ALLOW: "INFO",
        DefenderClassification.INFO: "INFO",
    }[classification]


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint in text for hint in hints)
