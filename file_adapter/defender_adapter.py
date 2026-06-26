# -*- coding: utf-8 -*-
"""Defender調査JSONLをLogViewer向けLogDictへ変換する。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from file_adapter.defender_rules import (
    DefenderClassification,
    classification_to_level,
    classify_executable,
    classify_path,
)
from logs.context_builder import plain_context
from logs.log_types import LogWhat, LogWhere


def adapt_defender_records(
    log_path: Path,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Defender系JSONLならLogViewer互換の辞書へ変換する。"""
    if not records:
        return records
    if not _looks_like_defender_records(records):
        return records
    return [_to_log_dict(log_path, row, index) for index, row in enumerate(records, start=1)]


def _looks_like_defender_records(records: list[dict[str, Any]]) -> bool:
    sample: dict[str, Any] = records[0]
    if {"time", "trace_id", "level", "what"} <= set(sample):
        return False
    defender_keys: set[str] = {
        "ThreatID",
        "ProcessName",
        "Resources",
        "FullName",
        "SignatureStatus",
        "SignerCertificate",
        "RegistryPath",
        "TaskName",
        "Execute",
        "Command",
    }
    return bool(defender_keys & set(sample))


def _to_log_dict(log_path: Path, row: dict[str, Any], index: int) -> dict[str, Any]:
    if "ThreatID" in row or "Resources" in row:
        return _adapt_threat_row(log_path, row, index)
    if "FullName" in row:
        return _adapt_executable_row(log_path, row, index)
    if "RegistryPath" in row:
        return _adapt_run_key_row(log_path, row, index)
    if "TaskName" in row or "Execute" in row:
        return _adapt_task_row(log_path, row, index)
    if "Command" in row and "Location" in row:
        return _adapt_startup_row(log_path, row, index)
    return _adapt_generic_row(log_path, row, index)


def _adapt_threat_row(log_path: Path, row: dict[str, Any], index: int) -> dict[str, Any]:
    resources: str = str(row.get("Resources", ""))
    process_name: str = str(row.get("ProcessName", "Unknown"))
    threat_id: str = str(row.get("ThreatID", index))
    status_text = DefenderClassification.ALERT
    risk_level: str = classification_to_level(status_text)
    summary_text: str = (
        f"ThreatID={threat_id} ProcessName={process_name} Resources={resources}"
    )
    return _build_log_dict(
        log_path=log_path,
        row=row,
        index=index,
        level=risk_level,
        time_text=_pick_time_text(row, "InitialDetection", "LastThreatStatus"),
        trace_seed=f"defender-threat-{threat_id}",
        message=_build_searchable_message(
            classification=status_text.value,
            source_kind="defender_threat_detection",
            body=f"defender threat detection: {summary_text}",
        ),
        where={"file": process_name if process_name != "Unknown" else str(log_path), "line": 1},
        what_extra={
            "action": "threat_detection",
            "status": status_text.value,
            "category": "defender",
        },
        context=plain_context(
            profile="defender",
            source_kind="defender_threat_detection",
            classification=status_text.value,
            summary=summary_text,
            threat_id=threat_id,
            threat_status_id=row.get("ThreatStatusID"),
            severity_id=row.get("SeverityID"),
            resources=resources,
            process_name=process_name,
        ),
    )


def _adapt_executable_row(log_path: Path, row: dict[str, Any], index: int) -> dict[str, Any]:
    full_name: str = str(row.get("FullName", ""))
    name: str = str(row.get("Name", ""))
    signature: str = str(row.get("SignatureStatus", ""))
    signer: str = str(row.get("SignerCertificate", ""))
    classification = classify_executable(full_name=full_name, signature=signature, signer=signer)
    risk_level: str = classification_to_level(classification)
    summary_text: str = (
        f"Name={name} Signature={signature or 'Unknown'} Signer={signer or 'None'}"
    )
    return _build_log_dict(
        log_path=log_path,
        row=row,
        index=index,
        level=risk_level,
        time_text=_pick_time_text(row, "LastWriteTime", "CreationTime", "LastAccessTime"),
        trace_seed=f"defender-exe-{full_name or index}",
        message=_build_searchable_message(
            classification=classification.value,
            source_kind="defender_executable_scan",
            body=f"defender executable item: {name} | {summary_text}",
        ),
        where={"file": full_name or str(log_path), "line": 1},
        what_extra={
            "action": "executable_scan",
            "status": classification.value,
            "category": "defender",
        },
        context=plain_context(
            profile="defender",
            source_kind="defender_executable_scan",
            classification=classification.value,
            summary=summary_text,
            executable_name=name,
            directory=row.get("Directory"),
            length=row.get("Length"),
            signature_status=signature,
            signer_certificate=signer,
            creation_time=row.get("CreationTime"),
            last_write_time=row.get("LastWriteTime"),
            last_access_time=row.get("LastAccessTime"),
        ),
    )


def _adapt_run_key_row(log_path: Path, row: dict[str, Any], index: int) -> dict[str, Any]:
    value_text: str = str(row.get("Value", ""))
    registry_path: str = str(row.get("RegistryPath", log_path))
    classification = (
        DefenderClassification.ALERT
        if "disableantispyware" in value_text.lower()
        else DefenderClassification.WATCH
    )
    summary_text: str = f"Name={row.get('Name', '')} Value={value_text}"
    return _build_log_dict(
        log_path=log_path,
        row=row,
        index=index,
        level=classification_to_level(classification),
        time_text=_fallback_now(),
        trace_seed=f"defender-run-key-{row.get('Name', index)}",
        message=_build_searchable_message(
            classification=classification.value,
            source_kind="defender_run_key",
            body=f"defender run key item: {summary_text}",
        ),
        where={"file": registry_path, "line": 1},
        what_extra={
            "action": "run_key_scan",
            "status": classification.value,
            "category": "defender",
        },
        context=plain_context(
            profile="defender",
            source_kind="defender_run_key",
            classification=classification.value,
            summary=summary_text,
            registry_path=registry_path,
            registry_name=row.get("Name"),
            registry_value=value_text,
        ),
    )


def _adapt_task_row(log_path: Path, row: dict[str, Any], index: int) -> dict[str, Any]:
    execute_text: str = str(row.get("Execute", ""))
    arguments_text: str = str(row.get("Arguments", ""))
    classification = classify_path(execute_text)
    summary_text: str = (
        f"TaskName={row.get('TaskName', '')} Execute={execute_text} Arguments={arguments_text or ''}"
    ).strip()
    return _build_log_dict(
        log_path=log_path,
        row=row,
        index=index,
        level=classification_to_level(classification),
        time_text=_fallback_now(),
        trace_seed=f"defender-task-{row.get('TaskName', index)}",
        message=_build_searchable_message(
            classification=classification.value,
            source_kind="defender_scheduled_task",
            body=f"defender scheduled task: {summary_text}",
        ),
        where={"file": execute_text or str(log_path), "line": 1},
        what_extra={
            "action": "scheduled_task_scan",
            "status": classification.value,
            "category": "defender",
        },
        context=plain_context(
            profile="defender",
            source_kind="defender_scheduled_task",
            classification=classification.value,
            summary=summary_text,
            task_name=row.get("TaskName"),
            task_path=row.get("TaskPath"),
            state=row.get("State"),
            execute=execute_text,
            arguments=arguments_text,
        ),
    )


def _adapt_startup_row(log_path: Path, row: dict[str, Any], index: int) -> dict[str, Any]:
    command_text: str = str(row.get("Command", ""))
    classification = classify_path(command_text)
    summary_text: str = f"Name={row.get('Name', '')} Command={command_text}"
    return _build_log_dict(
        log_path=log_path,
        row=row,
        index=index,
        level=classification_to_level(classification),
        time_text=_fallback_now(),
        trace_seed=f"defender-startup-{row.get('Name', index)}",
        message=_build_searchable_message(
            classification=classification.value,
            source_kind="defender_startup",
            body=f"defender startup item: {summary_text}",
        ),
        where={"file": command_text or str(log_path), "line": 1},
        what_extra={
            "action": "startup_scan",
            "status": classification.value,
            "category": "defender",
        },
        context=plain_context(
            profile="defender",
            source_kind="defender_startup",
            classification=classification.value,
            summary=summary_text,
            startup_name=row.get("Name"),
            command=command_text,
            location=row.get("Location"),
            user=row.get("User"),
        ),
    )


def _adapt_generic_row(log_path: Path, row: dict[str, Any], index: int) -> dict[str, Any]:
    return _build_log_dict(
        log_path=log_path,
        row=row,
        index=index,
        level="INFO",
        time_text=_fallback_now(),
        trace_seed=f"defender-generic-{index}",
        message=_build_searchable_message(
            classification=DefenderClassification.INFO.value,
            source_kind="defender_generic",
            body=f"defender record: {row}",
        ),
        where={"file": str(log_path), "line": 1},
        what_extra={
            "action": "generic_scan",
            "status": DefenderClassification.INFO.value,
            "category": "defender",
        },
        context=plain_context(
            profile="defender",
            source_kind="defender_generic",
            classification=DefenderClassification.INFO.value,
            summary="generic defender record",
        ),
    )


def _build_log_dict(
    *,
    log_path: Path,
    row: dict[str, Any],
    index: int,
    level: str,
    time_text: str,
    trace_seed: str,
    message: str,
    where: LogWhere,
    what_extra: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    what: LogWhat = cast(
        LogWhat,
        {
            "message": message,
            **what_extra,
        },
    )
    merged_context: dict[str, Any] = plain_context(
        source_file=str(log_path),
        source_row_index=index,
        original_record=row,
        **context,
    )
    return {
        "level": level,
        "time": time_text,
        "trace_id": trace_seed,
        "where": where,
        "what": what,
        "context": merged_context,
        "output": "file",
    }


def _build_searchable_message(*, classification: str, source_kind: str, body: str) -> str:
    """既存Viewer検索で拾いやすい検索トークンを本文へ付与する。"""
    return (
        f"[profile:defender] "
        f"[classification:{classification}] "
        f"[source_kind:{source_kind}] "
        f"{body}"
    )


def _pick_time_text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            parsed = _normalize_time(value.strip())
            if parsed:
                return parsed
    return _fallback_now()


def _normalize_time(value: str) -> str:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
        except ValueError:
            continue
    return value if "T" in value else _fallback_now()


def _fallback_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
