from __future__ import annotations

import unittest

from logs.query_error_bridge import build_query_error_response, build_query_error_text


class QueryErrorBridgeTests(unittest.TestCase):
    def test_missing_field_value_suggests_known_level_values(self) -> None:
        response = build_query_error_response(
            "level:",
            "Expected field value at position 6.",
        )

        self.assertEqual(6, response.position)
        self.assertEqual("field value", response.expected)
        self.assertIn("level:ERROR", response.suggestions)

        text = response.format_report()
        self.assertIn("level:", text)
        self.assertIn("     ^", text)
        self.assertIn("Did you mean:", text)

    def test_typo_field_suggests_nearest_field(self) -> None:
        text = build_query_error_text(
            "levle:ERROR",
            "Invalid field name: 'levle'.",
        )

        self.assertIn("level:ERROR", text)


if __name__ == "__main__":
    unittest.main()
