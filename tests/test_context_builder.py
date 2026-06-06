from __future__ import annotations

from datetime import datetime, timezone

from logs.context_builder import (
    context_for_apache_access,
    context_for_nginx_access,
    context_for_validation_error,
    ctx,
    detect_context_type,
    plain_context,
    wrap_context_value,
)
from logs.context_types import ContextType


def test_ctx_builds_typed_context_for_logger() -> None:
    context = ctx(retry=3, ok=True, missing=None)

    assert context["retry"] == {"type": "int", "value": 3}
    assert context["ok"] == {"type": "bool", "value": True}
    assert context["missing"] == {"type": "none", "value": None}


def test_plain_context_keeps_raw_values() -> None:
    context = plain_context(retry=3)

    assert context == {"retry": 3}


def test_detect_context_type_handles_none_and_datetime() -> None:
    value = datetime(2026, 6, 1, tzinfo=timezone.utc)

    assert detect_context_type(None) == ContextType.NONE
    assert wrap_context_value(value)["value"] == "2026-06-01T00:00:00+00:00"


def test_access_context_helpers_share_http_shape() -> None:
    apache = context_for_apache_access(ip="192.168.1.1", method="GET", path="/", status=200)
    nginx = context_for_nginx_access(ip="192.168.1.2", method="POST", path="/login", status=401)

    assert apache["server"] == "apache"
    assert apache["ip"] == "192.168.1.1"
    assert nginx["server"] == "nginx"
    assert nginx["status"] == 401


def test_validation_error_context_keeps_raw_record_out_of_message() -> None:
    raw = {"timestamp": "2026-06-01T09:00:00+00:00"}

    context = context_for_validation_error("missing time", raw)

    assert context["reason"] == "missing time"
    assert context["raw"] == raw
