# -*- coding: utf-8 -*-
"""サンプルのログファイルを生成するスクリプト。"""
#########################
# Author: F.Kurokawa
# Description:
# サンプルのログファイルを生成するスクリプト。
#########################

#########################

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

out = Path("/mnt/data/sample_production_logs_3000.jsonl")

levels: list[str] = ["INFO", "INFO", "INFO", "WARNING", "ERROR", "CRITICAL"]
modules: list[str] = ["auth", "network", "storage", "api", "scheduler", "database", "cache"]
ips: list[str] = ["203.0.113.10", "198.51.100.22", "45.12.88.9", "185.44.1.77", "192.0.2.55"]

start = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

with out.open("w", encoding="utf-8") as f:
    for i in range(3000): # ログ件数を指定可能
        ts: datetime = start + timedelta(seconds=i * 3)
        level: str = random.choice(levels)
        module: str = random.choice(modules)

        rec: dict[str, Any] = {
            "timestamp": ts.isoformat(),
            "level": level,
            "module": module,
            "event_id": f"EVT-{i:06d}",
        }

        # 攻撃イベント
        if 1200 <= i <= 1350:
            rec.update(
                {
                    "level": "WARNING" if i % 5 else "ERROR",
                    "message": "Login Failed",
                    "ip": random.choice(ips),
                    "username": random.choice(["admin", "root", "test", "guest"]),
                    "reason": "invalid_password",
                }
            )
        # DB障害
        elif 1800 <= i <= 1820:
            rec.update({"level": "ERROR", "module": "database", "message": "Database connection timeout", "retry": i - 1799})
        # クリティカル障害
        elif i == 1821:
            rec.update({"level": "CRITICAL", "module": "database", "message": "Primary database unavailable", "action": "failover_started"})
        elif i == 1822:
            rec.update({"level": "CRITICAL", "module": "api", "message": "Service degraded", "dependency": "database"})
        else:
            rec["message"] = random.choice(
                ["Request processed", "Cache refreshed", "Job completed", "Heartbeat", "User authenticated", "Configuration loaded"]
            )

        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(str(out))
# /mnt/data/sample_production_logs_3000.jsonl