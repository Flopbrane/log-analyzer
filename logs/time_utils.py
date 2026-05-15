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

from datetime import date, datetime, time, timedelta, timezone
from subprocess import CompletedProcess
from typing import Any, Callable, Literal, Protocol, TypeAlias, runtime_checkable
from zoneinfo import ZoneInfo, available_timezones

from logs.logger_config import LoggerConfig


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
def update_tzdata_if_year_changed(
    *,
    state_file: str | None = None,
    logger: LoggerLike | None = None,
) -> bool:
    """年が変わった時だけtzdataを最新版へ更新する"""
    import subprocess
    import sys
    from pathlib import Path

    current_year: int = date.today().year
    update_state_file: Path = (
        Path(state_file)
        if state_file
        else Path(__file__).with_name(".tzdata_updated_year")
    )

    try:
        last_updated_year: int | None = int(
            update_state_file.read_text(encoding="utf-8").strip()
        )
    except (FileNotFoundError, ValueError):
        last_updated_year = None
    except Exception as e:
        if logger:
            logger.warning(
                "tzdata update state read failed",
                context={"error": str(e), "state_file": str(update_state_file)},
            )
        last_updated_year = None

    if last_updated_year == current_year:
        return False

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
        return False

    try:
        import tzdata

        tzdata_version: str = getattr(
            tzdata,
            "__version__",
            "unknown",
        )

    except Exception:
        tzdata_version = "unknown"

    if result.returncode != 0:
        if logger:
            logger.warning(
                "tzdata update failed",
                context={
                    "returncode": result.returncode,
                    "stderr": result.stderr.strip(),
                },
            )
        return False

    try:
        update_state_file.write_text(str(current_year), encoding="utf-8")
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
                "tzdata_version": tzdata_version,
                "stdout": result.stdout.strip(),
                "python": sys.executable,
            },
        )

    return True


if __name__ == "__main__":
    update_tzdata_if_year_changed()
