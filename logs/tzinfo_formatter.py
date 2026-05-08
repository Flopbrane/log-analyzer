# -*- coding: utf-8 -*-
"""zoneinfoからの情報を使いやすいように纏めるモジュール"""
#########################
# Author: F.Kurokawa
# Description:
# zoneinfoからの情報を使いやすいように纏めるモジュール
#########################

from __future__ import annotations

from dataclasses import dataclass

from zoneinfo import available_timezones


@dataclass(slots=True)
class TimeZoneItem:
    zone: str
    area: str
    city: str
    label: str

@dataclass(slots=True)
class TimeZoneData:
    area_list: list[str]
    area_map: dict[str, list[TimeZoneItem]]

EXCLUDED_PREFIXES: tuple[str, ...] = (
    "Etc/",
    "GMT",
    "UTC",
    "SystemV/",
    "posix/",
    "right/",
    "US/",
    "Canada/",
    "Mexico/",
    "Brazil/",
    "Chile/",
    "Argentina/",
)

def is_excluded_prefix(tz: str) -> bool:
    """タイムゾーンが除外対象か判定"""

    if "/" not in tz:
        return True

    return any(
        tz.startswith(prefix)
        for prefix in EXCLUDED_PREFIXES
        )

def build_timezone_items() -> list[TimeZoneItem]:
    """zoneinfoからの情報を使いやすいように纏める関数"""
    items: list[TimeZoneItem] = []
    area: str
    city: str
    label: str

    for tz in available_timezones():
        # "/" を含まないものを除外
        if "/" not in tz:
            continue

        if is_excluded_prefix(tz):
            continue

        area, city = tz.split("/", 1)
        
        label = build_tz_label(tz)
        
        items.append(
            TimeZoneItem(
                zone=tz,
                area=area,
                city=city,
                label=label
                ))

    return items


def build_area_map(
    items: list[TimeZoneItem]
) -> dict[str, list[TimeZoneItem]]:
    """tzinfoに含まれているarea情報をkeyとしてメインの辞書を作成する関数"""
    area_map: dict[str, list[TimeZoneItem]] = {}
    
    for item in items:
        area_map.setdefault(item.area, []).append(item)
    
    for area_items in area_map.values():
        area_items.sort(key=lambda x: x.city)

    return area_map

def build_tz_label(zone: str) -> str:
    """タイムゾーンのラベルを生成する関数"""
    area: str
    city: str

    area, city = zone.split("/", 1)

    return f"{area} - {city.replace('/', ' / ')}"

def build_timezone_data() -> TimeZoneData:
    """Viewer用のTimeZoneデータをまとめて生成"""

    items: list[TimeZoneItem] = build_timezone_items()

    area_map: dict[str, list[TimeZoneItem]] = build_area_map(items)

    area_list: list[str] = sorted(area_map.keys())

    return TimeZoneData(
        area_list=area_list,
        area_map=area_map,
    )
