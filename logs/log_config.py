# -*- coding: utf-8 -*-
"""基準時間精度を設定する"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class LoggerConfig:
    """基準時間精度を設定する"""
    time_precision: str = "second"  # or "micro"
    timezone: str = "UTC"
    time_format: str = "%Y-%m-%d %H:%M:%S"

def load_viewer_config() -> dict[str, Any]:
    """ログビューワの設定をJSONファイルから読み込む。"""
    config_path: str = os.path.join(os.path.dirname(__file__), "log_config.json")
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}

def save_viewer_config( config: dict[str, Any], ) -> None:
    """ログビューワの設定をJSONファイルへ保存する。"""
    config_path: str = os.path.join(os.path.dirname(__file__), "log_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
