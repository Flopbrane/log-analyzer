# -*- coding: utf-8 -*-
"""LogViewerの言語選択ヘルパー。"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal, TypeAlias

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lang import en, ja

LanguageCode: TypeAlias = Literal["ja", "en"]

DEFAULT_LANGUAGE: LanguageCode = "ja"

TRANSLATIONS: dict[LanguageCode, dict[str, str]] = {
    "ja": ja.TRANSLATIONS,
    "en": en.TRANSLATIONS,
}

TIMEZONE_AREAS: dict[LanguageCode, dict[str, str]] = {
    "ja": ja.TIMEZONE_AREAS,
    "en": en.TIMEZONE_AREAS,
}

TIMEZONE_CITIES: dict[LanguageCode, dict[str, str]] = {
    "ja": ja.TIMEZONE_CITIES,
    "en": en.TIMEZONE_CITIES,
}


TIMEZONE_COUNTRIES: dict[LanguageCode, dict[str, str]] = {
    "ja": ja.TIMEZONE_COUNTRIES,
    "en": en.TIMEZONE_COUNTRIES,
}

def normalize_language(language: str) -> LanguageCode:
    """ユーザー向け言語値を、サポートされている言語コードに正規化します。"""
    normalized: str = language.strip().lower()
    if normalized in {"en", "english"}:
        return "en"
    return "ja"


def translate(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    """UI文字列を翻訳して返す。日本語、次にキーの順でフォールバックする。"""
    language_code: LanguageCode = normalize_language(language)
    return TRANSLATIONS.get(language_code, {}).get(
        key,
        TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key),
    )


def translate_timezone_area(area: str, language: str = DEFAULT_LANGUAGE) -> str:
    """タイムゾーンのエリア名を翻訳して返す。"""
    language_code: LanguageCode = normalize_language(language)
    return TIMEZONE_AREAS.get(language_code, {}).get(
        area,
        TIMEZONE_AREAS[DEFAULT_LANGUAGE].get(area, area),
    )


def translate_timezone_city(city: str, language: str = DEFAULT_LANGUAGE) -> str:
    """タイムゾーンの都市名を翻訳して返す。"""
    language_code: LanguageCode = normalize_language(language)
    readable_city: str = city.replace("_", " ").replace("/", " / ")
    return TIMEZONE_CITIES.get(language_code, {}).get(city, readable_city)


def translate_timezone_country(city: str, language: str = DEFAULT_LANGUAGE) -> str:
    """タイムゾーンの国名を翻訳して返す。"""
    language_code: LanguageCode = normalize_language(language)
    readable_city: str = city.replace("_", " ").replace("/", " / ")
    return TIMEZONE_COUNTRIES.get(language_code, {}).get(city, readable_city)


def format_utc_offset(zone: str) -> str:
    """IANAタイムゾーンの現在のUTCオフセットを返す。"""
    hours: int
    minutes: int
    try:
        local_now: datetime = datetime.now(ZoneInfo(zone))
    except ZoneInfoNotFoundError:
        return "UTC?"

    offset: timedelta | None = local_now.utcoffset()
    if offset is None:
        return "UTC?"

    total_minutes: int = int(offset.total_seconds() // 60)
    sign: Literal['+'] | Literal['-'] = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"

def build_timezone_display(
    city: str,
    utc_offset: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """ローカライズされたタイムゾーン表示ラベルを作成する。"""
    city_text: str = translate_timezone_city(city, language)
    country_text: str = translate_timezone_country(
        city,
        language,
    )
    return f"{country_text}/{city_text} ({utc_offset})"


def build_timezone_label(
    zone: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """IANAタイムゾーン名からローカライズされたラベルを作成する。"""

    _: str
    city: str
    country_text: str
    city_text: str
    utc_offset: str

    if "/" not in zone:
        return zone

    _, city = zone.split("/", 1)

    country_text = translate_timezone_country(
        city,
        language,
    )

    city_text = translate_timezone_city(
        city,
        language,
    )

    utc_offset = format_utc_offset(zone)

    return (
        f"{city_text}, "
        f"{country_text} "
        f"({utc_offset})"
    )
