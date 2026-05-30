from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from query_engine.adapters.base import normalize_document
from query_engine.adapters.json_adapter import DocumentLoadIssue, iter_json_documents
from query_engine.adapters.tabular import row_to_document
from query_engine.models import Document


class QueryDocumentAdapterTests(unittest.TestCase):
    def test_normalize_document_keeps_stable_schema(self) -> None:
        document: Document = normalize_document(
            {"level": "ERROR", "message": "disk failure"},
            id="log-1",
            source="memory",
            metadata={"line": 10},
        ).to_mapping()

        self.assertEqual("log-1", document["id"])
        self.assertEqual("memory", document["source"])
        self.assertIn("disk failure", document["text"])
        self.assertEqual("ERROR", document["level"])
        self.assertEqual("ERROR", document["fields"]["level"])
        self.assertEqual(10, document["metadata"]["line"])

    def test_row_to_document_uses_schema_compatible_mapping(self) -> None:
        document: Document = row_to_document(
            {"cpu": 82.5, "status": "warning"},
            source="metrics.csv",
            table="metrics",
            row_number=2,
        )

        self.assertEqual("metrics.csv:metrics:2", document["id"])
        self.assertEqual(82.5, document["cpu"])
        self.assertEqual(82.5, document["fields"]["cpu"])
        self.assertEqual(2, document["metadata"]["row_number"])

    def test_iter_json_documents_skips_broken_jsonl_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path: Path = Path(tmp_dir) / "logs.jsonl"
            path.write_text(
                '{"level": "INFO", "message": "ok"}\n'
                '{"level": "BROKEN", "message": \n'
                '{"level": "ERROR", "message": "failed"}\n',
                encoding="utf-8",
            )

            issues: list[DocumentLoadIssue] = []
            documents: list[Document] = list(iter_json_documents(path, issues=issues))

        self.assertEqual(2, len(documents))
        self.assertEqual(["INFO", "ERROR"], [doc["level"] for doc in documents])
        self.assertEqual(1, len(issues))
        self.assertEqual(2, issues[0].line_number)


if __name__ == "__main__":
    unittest.main()
