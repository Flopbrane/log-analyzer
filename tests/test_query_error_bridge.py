# cspell:ignore levle

from __future__ import annotations

import unittest

from logs.query_error_bridge import QueryErrorResponse, build_query_error_response, build_query_error_text


class QueryErrorBridgeTests(unittest.TestCase):
    def test_missing_field_value_suggests_known_level_values(self) -> None:
        response: QueryErrorResponse = build_query_error_response(
            "level:",
            "Expected field value at position 6.",
        )

        self.assertEqual(6, response.position)
        self.assertEqual("field value", response.expected)
        self.assertIn("level:ERROR", response.suggestions)

        text: str = response.format_report()
        self.assertIn("level:", text)
        self.assertIn("     ^", text)
        self.assertIn("Did you mean:", text)

    def test_typo_field_suggests_nearest_field(self) -> None:
        text: str = build_query_error_text(
            "levle:ERROR",  # cspell:disable-line
            "Invalid field name: 'levle'.",  # cspell:disable-line
        )

        self.assertIn("level:ERROR", text)

    def test_datetime_suggestions_use_first_log_time(self) -> None:
        rows: list[dict[str, str]] = [
            {"time": "2026-05-28T01:23:45+00:00"},
            {"time": "2026-05-29T10:00:00+00:00"},
        ]

        date_text: str = build_query_error_text(
            "date:",
            "Expected field value at position 6.",
            rows,
            "Asia/Tokyo",
        )
        local_date_text: str = build_query_error_text(
            "local_date:",
            "Expected field value at position 12.",
            rows,
            "Asia/Tokyo",
        )
        local_clock_text: str = build_query_error_text(
            "local_clock:",
            "Expected field value at position 13.",
            rows,
            "Asia/Tokyo",
        )

        self.assertIn("date:2026-05-28 01:23:45", date_text)
        self.assertIn("local_date:2026-05-28", local_date_text)
        self.assertIn("local_clock:10:23:45", local_clock_text)


if __name__ == "__main__":
    unittest.main()
