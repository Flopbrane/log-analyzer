# pylint: disable=W0611, W0107, W0718
# pyright: reportUnnecessaryIsInstance=false
# # -*- coding: utf-8 -*-
"""時間関連のユーティリティ関数"""
#########################
# Author: F.Kurokawa
# Description:
# 時間関連のユーティリティ関数
#########################
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Callable, Literal, Protocol, TypeAlias, runtime_checkable

from zoneinfo import ZoneInfo, available_timezones

from logs.log_config import LoggerConfig

TZDATA_REFERENCE_FILE = ".tzdata_ver_reference"
TZDATA_PYPI_URL = "https://pypi.org/pypi/tzdata/json"


@dataclass(frozen=True, slots=True)
class TzdataUpdateResult:
    """tzdata更新確認の結果。"""

    checked: bool
    updated: bool
    installed_version: str
    latest_version: str
    reference_version: str
    message: str


@runtime_checkable
class LoggerLike(Protocol):
    """Loggerのインターフェース定義（完全版）
    💥 Protocolは「実装」ではなく「型の約束」です
    🚀【実際の動き】
    コード👇
    def func(logger: LoggerLike):
        logger.info("test", context={"a": 1})
    👉 呼び出し👇
    logger = get_logger()  # ← AppLogger
    func(logger)
    👉 実際に動くのは👇
    AppLogger.info(...)
    """

    def debug(self, message: str, **kw: Any) -> None:
        """デバッグレベルのログを出力する"""
        ...

    def info(self, message: str, **kw: Any) -> None:
        """情報レベルのログを出力する"""
        ...

    def warning(self, message: str, **kw: Any) -> None:
        """警告レベルのログを出力する"""
        ...

    def error(self, message: str, **kw: Any) -> None:
        """エラーレベルのログを出力する"""
        ...

    def critical(self, message: str, **kw: Any) -> None:
        """緊急レベルのログを出力する"""
        ...

# =========================
# 型定義
# =========================
# ISO文字列専用
ISODateTimeStr: TypeAlias = str

# UNIX時間専用
UnixTime: TypeAlias = float | int

# datetimeに対しての安全な入力型
DateLike: TypeAlias = datetime | date | str | int | float | None

# JSTタイムゾーン
#JST = timezone(timedelta(hours=9))


# =========================
# UnixTime → UTC日時文字列表示
# =========================
def format_unix_to_utc_time(ts: UnixTime | None) -> str:
    """UNIXTIME_to_UTC"""
    dt: datetime | None = to_utc_datetime(ts)
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_unix_to_utc_iso(ts: UnixTime | None) -> str:
    """UNIXTIME_to_UTC"""
    dt: datetime | None = to_utc_datetime(ts)
    if dt is None:
        return ""
    return dt.isoformat(timespec="seconds")


# =========================
# UTCの時間精度を変更する
# =========================
def now_utc(config: LoggerConfig | None = None) -> datetime:
    """UTCの時間精度を変更する"""
    dt: datetime = datetime.now(timezone.utc)

    precision = "second"
    if config:
        precision: str = config.time_precision

    if precision == "second":
        return dt.replace(microsecond=0)

    return dt


# =========================
# UTC変換
# =========================
def _resolve_timezone(
    tz: str | ZoneInfo,
    logger: LoggerLike | None = None,
) -> ZoneInfo | timezone | None:
    """tzをtzinfoへ変換する"""
    if isinstance(tz, ZoneInfo):
        return tz

    try:
        return ZoneInfo(tz)
    except Exception as e:
        if logger:
            logger.warning(
                "Invalid timezone",
                context={"tz": tz, "error": str(e)},
            )
        return None


def to_utc_datetime_from_world_local_dt(
    value: DateLike = None,
    tz: str | ZoneInfo = "Asia/Tokyo",
    *,
    logger: LoggerLike | None = None,
) -> datetime | None:
    """ローカル日時をUTCのdatetimeに変換する"""

    if value is None:
        return None

    # 🔹 datetime
    if isinstance(value, datetime):
        if value.tzinfo is None:
            tzinfo = _resolve_timezone(tz, logger)
            if tzinfo is None:
                return None
            return (
                value.replace(tzinfo=tzinfo)
                .astimezone(timezone.utc)
                .replace(microsecond=0)
            )
        return value.astimezone(timezone.utc).replace(microsecond=0)

    # 🔹 time（非対応）
    if isinstance(value, time):
        if logger:
            logger.warning("time単体はサポートされていません")
        return None

    # 🔹 UNIX TIME
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(microsecond=0)
        except Exception as e:
            if logger:
                logger.warning(
                    "Invalid UNIX timestamp",
                    context={"value": value, "error": str(e)},
            )
            return None

    tzinfo: ZoneInfo | timezone | None = _resolve_timezone(tz, logger)
    
    if tzinfo is None:
        return None

    # 🔹 date → 00:00
    if isinstance(value, date):
        return (
            datetime.combine(value, time(0, 0), tzinfo=tzinfo)
            .astimezone(timezone.utc)
            .replace(microsecond=0)
        )

    # 🔹 str（ISO）
    if isinstance(value, str):
        try:
            dt: datetime = datetime.fromisoformat(value).replace(microsecond=0)
        except ValueError:
            if logger:
                logger.warning(
                    "Invalid datetime string",
                    context={"value": value},
                )
            return None

        if dt.tzinfo is None:
            return (
                dt.replace(tzinfo=tzinfo)
                .astimezone(timezone.utc)
                .replace(microsecond=0)
            )

        return dt.astimezone(timezone.utc).replace(microsecond=0)

    # 🔹 未対応型
    if logger:
        logger.warning(
            "Unsupported type",
            context={"type": str(type(value))},
        )

    return None


to_utc_datetime: Callable[..., datetime | None] = to_utc_datetime_from_world_local_dt


# =========================
# ISO（UTC_str）
# =========================
def to_utc_iso(value: DateLike) -> str | None:
    """値をUTCのISOフォーマット文字列に変換する"""
    dt: datetime | None = to_utc_datetime_from_world_local_dt(value)
    if dt is None:
        return None
    return dt.isoformat()


# ========================
# Local_Time changer
# ========================
def to_world_local_datetime(
    value: DateLike,
    tz: str | ZoneInfo = "Asia/Tokyo",
    *,
    logger: LoggerLike | None = None,
) -> datetime | None:
    """任意タイムゾーンdatetimeへ変換（最終出口）"""

    dt: datetime | None = to_utc_datetime_from_world_local_dt(value, logger=logger)
    if dt is None:
        return None

    try:
        tzinfo: ZoneInfo = ZoneInfo(tz) if isinstance(tz, str) else tz
        return dt.astimezone(tzinfo)

    except Exception as e:
        if not tz:
            tz = "Asia/Tokyo (default)"
            return dt.astimezone(ZoneInfo("Asia/Tokyo"))
        
        if logger:
            logger.warning(
                f"Invalid timezone: {tz}",
                context={"error": str(e)},
            )
        return None


def to_world_local_str(
    value: DateLike,
    tz: str | ZoneInfo = "Asia/Tokyo",
    *,
    logger: LoggerLike | None = None,
) -> str:
    """任意タイムゾーンstrへ変換（最終出口）"""

    dt: datetime | None = to_world_local_datetime(value, tz, logger=logger)
    if dt is None:
        return ""

    return dt.isoformat(timespec="seconds")


# ========================
# Local_list
# ========================
def list_timezones_formatted() -> list[tuple[str, str]]:
    """
    TimeZone一覧を取得して、
    (内部名, 表示名) のタプルで返す

    例:
    ("Asia/Tokyo", "Tokyo (UTC+09:00)")
    """

    now_utc_dt: datetime = datetime.now(timezone.utc)

    results: list[tuple[str, str]] = []

    for tz_name in sorted(available_timezones()):
        try:
            tz = ZoneInfo(tz_name)
            local_dt: datetime = now_utc_dt.astimezone(tz)

            offset: timedelta | None = local_dt.utcoffset()
            if offset is None:
                continue

            total_seconds = int(offset.total_seconds())
            hours: int = total_seconds // 3600
            minutes: int = abs((total_seconds % 3600) // 60)

            sign: Literal['+'] | Literal['-'] = "+" if hours >= 0 else "-"
            offset_str: str = f"UTC{sign}{abs(hours):02d}:{minutes:02d}"

            # 表示名（最後の部分だけ）
            display_name: str = tz_name.split("/")[-1]

            label: str = f"{display_name} ({offset_str})"

            results.append((tz_name, label))

        except Exception:
            # 一部のTimeZoneで失敗することがあるので無視
            continue

    return results


# ========================
# tzdata auto updater
# ========================
def get_installed_tzdata_version() -> str:
    """現在importできるtzdataパッケージのバージョンを返す。"""
    try:
        import tzdata
    except Exception:
        return "not-installed"
    return str(getattr(tzdata, "__version__", "unknown"))


def get_latest_tzdata_version(timeout: float = 10.0) -> str | None:
    """PyPIから公開済みの最新tzdataバージョンを取得する。"""
    try:
        with urllib.request.urlopen(TZDATA_PYPI_URL, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None

    version = payload.get("info", {}).get("version")
    return version if isinstance(version, str) and version else None


def update_tzdata_if_needed(
    *,
    state_file: str | None = None,
    logger: LoggerLike | None = None,
) -> TzdataUpdateResult:
    """tzdataの最新公開バージョンを確認し、必要なら更新する。"""
    update_state_file: Path = (
        Path(state_file)
        if state_file
        else Path(__file__).with_name(TZDATA_REFERENCE_FILE)
    )
    current_year = str(date.today().year)

    try:
        reference_version = update_state_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        reference_version = ""
    except Exception as e:
        if logger:
            logger.warning(
                "tzdata update state read failed",
                context={"error": str(e), "state_file": str(update_state_file)},
            )
        reference_version = ""

    installed_version = get_installed_tzdata_version()
    latest_version = get_latest_tzdata_version()
    if latest_version is None:
        if not reference_version:
            update_state_file.write_text(f"{current_year}:unknown", encoding="utf-8")
        return TzdataUpdateResult(
            checked=False,
            updated=False,
            installed_version=installed_version,
            latest_version="unknown",
            reference_version=reference_version,
            message="tzdata latest version check skipped or failed",
        )

    expected_reference = f"{current_year}:{latest_version}"
    if reference_version == expected_reference and installed_version == latest_version:
        return TzdataUpdateResult(
            checked=True,
            updated=False,
            installed_version=installed_version,
            latest_version=latest_version,
            reference_version=reference_version,
            message="tzdata already up to date",
        )

    try:
        result: CompletedProcess[str] = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "tzdata",
            ],  # sys.executable =「今動いてるPython」でpip実行 → venvのPythonにインストールされる
            capture_output=True,
            check=False,
            text=True,
        )
    except Exception as e:
        if logger:
            logger.warning("tzdata update failed", context={"error": str(e)})
        return TzdataUpdateResult(
            checked=True,
            updated=False,
            installed_version=installed_version,
            latest_version=latest_version,
            reference_version=reference_version,
            message=str(e),
        )

    if result.returncode != 0:
        if logger:
            logger.warning(
                "tzdata update failed",
                context={
                    "returncode": result.returncode,
                    "stderr": result.stderr.strip(),
                },
            )
        return TzdataUpdateResult(
            checked=True,
            updated=False,
            installed_version=installed_version,
            latest_version=latest_version,
            reference_version=reference_version,
            message=result.stderr.strip() or "tzdata update failed",
        )

    updated_version = get_installed_tzdata_version()

    try:
        update_state_file.write_text(f"{current_year}:{updated_version}", encoding="utf-8")
    except Exception as e:
        if logger:
            logger.warning(
                "tzdata update state write failed",
                context={"error": str(e), "state_file": str(update_state_file)},
            )

    if logger:
        logger.info(
            "tzdata updated",
            context={
                "year": current_year,
                "tzdata_version": updated_version,
                "latest_version": latest_version,
                "stdout": result.stdout.strip(),
                "python": sys.executable,
            },
        )

    return TzdataUpdateResult(
        checked=True,
        updated=updated_version != installed_version,
        installed_version=updated_version,
        latest_version=latest_version,
        reference_version=f"{current_year}:{updated_version}",
        message="tzdata updated",
    )


def update_tzdata_if_year_changed(
    *,
    state_file: str | None = None,
    logger: LoggerLike | None = None,
) -> bool:
    """後方互換用: tzdata更新が発生したかだけを返す。"""
    return update_tzdata_if_needed(state_file=state_file, logger=logger).updated


if __name__ == "__main__":
    update_tzdata_if_year_changed()
