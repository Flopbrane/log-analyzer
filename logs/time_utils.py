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
from typing import Any, Literal, Protocol, TypeAlias, Union, runtime_checkable
from zoneinfo import ZoneInfo, available_timezones

from logs.logger_config import LoggerConfig


@runtime_checkable
class LoggerLike(Protocol):
    """Loggerのインターフェース定義（完全版）"""

    def debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        """デバッグレベルのログを出力する"""
        pass

    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        """情報レベルのログを出力する"""
        pass

    def warning(self, message: str, context: dict[str, Any] | None = None) -> None:
        """警告レベルのログを出力する"""
        pass

    def error(self, message: str, context: dict[str, Any] | None = None) -> None:
        """エラーレベルのログを出力する"""
        pass

    def critical(self, message: str, context: dict[str, Any] | None = None) -> None:
        """緊急レベルのログを出力する"""
        pass

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
JST = timezone(timedelta(hours=9))


# =========================
# UnixTime → UTC日時表示(core_DATA用)
# =========================
def unix_to_utc_datetime(ts: Union[UnixTime, None]) -> datetime | None:
    """UNIX時間 → UTCDateTime"""
    if ts is None:
        return None
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except Exception as e:
        print(f"Error as {e}")
        return None


# =========================
# UnixTime → UTC日時文字列表示
# =========================
def format_unix_to_utc_time(ts: UnixTime | None) -> str:
    """UNIXTIME_to_UTC"""
    dt: datetime | None = unix_to_utc_datetime(ts)
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_unix_to_utc_iso(ts: UnixTime | None) -> str:
    """UNIXTIME_to_UTC"""
    dt: datetime | None = unix_to_utc_datetime(ts)
    if dt is None:
        return ""
    return dt.isoformat(timespec="seconds")


# =========================
# UTC現在時刻
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
def to_utc_datetime(
    value: DateLike = None,
    *,
    logger: LoggerLike | None = None
    ) -> datetime | None:
    """値をUTCのdatetimeに変換する"""
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=JST).astimezone(timezone.utc)
        return value.astimezone(timezone.utc).replace(microsecond=0)

    # dateはJSTの00:00として扱う
    if isinstance(value, date):
        return datetime.combine(
            value,
            time(0, 0),
            tzinfo=JST).astimezone(timezone.utc).replace(microsecond=0)

    if isinstance(value, time): # timeだけでは、UTC変換に疑問が残るため使用しない
        if logger:
            logger.warning("time単体はサポートされていません")
        return None

        # 🔥 ここ追加
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(microsecond=0)
        except Exception:
            return None

    if isinstance(value, str):
        try:
            dt: datetime = datetime.fromisoformat(value).replace(microsecond=0)
        except ValueError:
            if logger:
                logger.warning(f"Invalid datetime string: {value}")
            return None

        if dt.tzinfo is None:
            return dt.replace(tzinfo=JST).astimezone(timezone.utc).replace(microsecond=0)

        return dt.astimezone(timezone.utc).replace(microsecond=0)

    if logger:
        logger.warning(f"Unsupported type: {type(value)}")

    return None


def to_utc_datetime_from_local_dt(
    value: DateLike = None,
    tz: str | ZoneInfo = "Asia/Tokyo",
    *,
    logger: LoggerLike | None = None,
) -> datetime | None:
    """ローカル日時をUTCのdatetimeに変換する"""

    if value is None:
        return None

    # 🔹 tzをZoneInfoに統一
    try:
        tzinfo: ZoneInfo = ZoneInfo(tz) if isinstance(tz, str) else tz
    except Exception as e:
        if logger:
            logger.warning(
                "Invalid timezone",
                context={"tz": tz, "error": str(e)},
            )
        return None

    # 🔹 datetime
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return (
                value.replace(tzinfo=tzinfo)
                .astimezone(timezone.utc)
                .replace(microsecond=0)
            )
        return value.astimezone(timezone.utc).replace(microsecond=0)

    # 🔹 date → 00:00
    if isinstance(value, date):
        return (
            datetime.combine(value, time(0, 0), tzinfo=tzinfo)
            .astimezone(timezone.utc)
            .replace(microsecond=0)
        )

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


# =========================
# ISO（UTC）
# =========================
def to_utc_iso(value: DateLike) -> str | None:
    """値をUTCのISOフォーマット文字列に変換する"""
    dt: datetime | None = to_utc_datetime(value)
    if dt is None:
        return None
    return dt.isoformat()


# =========================
# JST変換
# =========================
def to_jst_datetime(value: DateLike) -> datetime | None:
    """値をJSTのdatetimeに変換する（表示専用）"""
    dt: datetime | None = to_utc_datetime(value)
    if dt is None:
        return None
    return dt.astimezone(JST)


def to_jst_str(value: DateLike) -> str | None:
    """値をJSTの文字列に変換する(表示用)"""
    dt: datetime | None = to_utc_datetime(value)
    if dt is None:
        return ""
    return dt.astimezone(JST).isoformat(timespec="seconds")


# ========================
# Local_Time changer
# ========================
def to_local_datetime(
    value: DateLike,
    tz: str | ZoneInfo = "Asia/Tokyo",
    *,
    logger: LoggerLike | None = None,
) -> datetime | None:
    """任意タイムゾーンdatetimeへ変換（最終出口）"""

    dt: datetime | None = to_utc_datetime(value, logger=logger)
    if dt is None:
        return None

    try:
        tzinfo: ZoneInfo = ZoneInfo(tz) if isinstance(tz, str) else tz
        return dt.astimezone(tzinfo)

    except Exception as e:
        if logger:
            logger.warning(
                f"Invalid timezone: {tz}",
                context={"error": str(e)},
            )
        return None


def to_local_str(
    value: DateLike,
    tz: str | ZoneInfo = "Asia/Tokyo",
    *,
    logger: LoggerLike | None = None,
) -> str:
    """任意タイムゾーンstrへ変換（最終出口）"""

    dt: datetime | None = to_local_datetime(value, tz, logger=logger)
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
