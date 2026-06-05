from __future__ import annotations

from summary_engine.aggregators.ip_aggregator import aggregate_ips
from summary_engine.aggregators.time_aggregator import aggregate_dates, aggregate_hours
from summary_engine.aggregators.user_aggregator import aggregate_users


def test_optional_aggregators_count_common_context_fields() -> None:
    logs = [
        {
            "time": "2026-06-01T09:15:00+00:00",
            "context": {"ip": "192.168.1.1", "user": "alice"},
        },
        {
            "time": "2026-06-01T09:45:00+00:00",
            "context": {"client_ip": "192.168.1.1", "user_id": "alice"},
        },
        {
            "time": "2026-06-02T10:00:00+00:00",
            "context": {
                "original_row": {
                    "ip": "192.168.1.2",
                    "user": {"id": "bob"},
                }
            },
        },
    ]

    assert aggregate_ips(logs)[0].key == "192.168.1.1"
    assert aggregate_ips(logs)[0].count == 2
    assert aggregate_users(logs)[0].key == "alice"
    assert aggregate_users(logs)[0].count == 2
    assert aggregate_dates(logs)[0].key == "2026-06-01"
    assert aggregate_dates(logs)[0].count == 2
    assert aggregate_hours(logs)[0].key == "2026-06-01T09:00:00+00:00"
    assert aggregate_hours(logs)[0].count == 2
