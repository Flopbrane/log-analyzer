# -*- coding: utf-8 -*-
"""コンテキスト集計モジュール
context_aggregator.pyは、ログデータのコンテキスト情報を集計し、要約エンジンに提供する役割を担います。
このモジュールは、ログデータの条件別統計を作成し、人間が理解しやすい要約を生成するための基盤を提供します。"""
#########################
# Author: F.Kurokawa
# Description:
#
#########################

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Iterable, Mapping, cast

from summary_engine.summary_types import NumericStats


def aggregate_numeric_context(logs: Iterable[Mapping[str, Any]]) -> dict[str, NumericStats]:
    """context内にある数値値の基本統計を返す。"""
    values_by_field: dict[str, list[float]] = defaultdict(list)
    for log in logs:
        context: object = log.get("context", {})
        if isinstance(context, Mapping):
            context_map: Mapping[str, Any] = cast(
                Mapping[str, Any],
                context,
            )
            if set(context_map.keys()) == {"type", "value"}:
                context_value: object = context_map.get("value")
                if isinstance(context_value, Mapping):
                    context_map = cast(
                        Mapping[str, Any],
                        context_value,
                    )
                else:
                    continue

            _collect_numeric_values(
                context_map,
                "",
                values_by_field,
            )

    return {
        field: NumericStats(
            field=f"context.{field}",
            count=len(values),
            minimum=min(values),
            maximum=max(values),
            average=statistics.mean(values),
            median=statistics.median(values),
        )
        for field, values in sorted(values_by_field.items())
        if values
    }


def _collect_numeric_values(
    value: object,
    prefix: str,
    values_by_field: dict[str, list[float]],
) -> None:
    """値が数値であればvalues_by_fieldに追加する。Mappingなら再帰的に探索する。"""
    if value is None:
        return
    if isinstance(value, Mapping):
        mapping_value: Mapping[str, Any] = cast(
            Mapping[str, Any],
            value,
        )

        if set(mapping_value.keys()) == {"type", "value"}:
            _collect_numeric_values(
                mapping_value.get("value"),
                prefix,
                values_by_field,
            )
            return

        for key, child in mapping_value.items():
            child_prefix: str = (
                f"{prefix}.{key}"
                if prefix
                else key
            )
            _collect_numeric_values(
                child,
                child_prefix,
                values_by_field,
            )
    else:
        if isinstance(value, (int, float)):
            values_by_field[prefix].append(float(value))
