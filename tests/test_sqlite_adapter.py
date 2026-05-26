from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from query_engine.adapters.sqlite_adapter import SQLiteDocumentStore
from query_engine.models import Document


class SQLiteAdapterTests(unittest.TestCase):
    def test_store_searches_documents_by_text_and_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "logs.sqlite"
            documents: list[Document] = [
                {
                    "level": "ERROR",
                    "message": "disk failure",
                    "context": {"retry": 3},
                },
                {
                    "level": "INFO",
                    "message": "healthy",
                    "context": {"retry": 0},
                },
            ]

            with SQLiteDocumentStore(db_path) as store:
                self.assertEqual(2, store.add_documents(documents))

                error_results = store.search("level:ERROR")
                self.assertEqual(1, len(error_results))
                self.assertEqual("disk failure", error_results[0].document["message"])

                retry_results = store.search("context.retry >= 1")
                self.assertEqual(1, len(retry_results))
                self.assertEqual("ERROR", retry_results[0].document["level"])

                batches = list(store.iter_search("failure", batch_size=1))
                self.assertEqual(1, len(batches))
                self.assertEqual(0, batches[0].offset)
                self.assertEqual("disk failure", batches[0].results[0].document["message"])


if __name__ == "__main__":
    unittest.main()
