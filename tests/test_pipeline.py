import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import refresh_free_data as refresh

class PipelineTests(unittest.TestCase):
    def test_parse_float(self):
        self.assertEqual(refresh.parse_float("$1,234.50"), 1234.5)
        self.assertIsNone(refresh.parse_float("not-a-number"))

    def test_atomic_json_preserves_valid_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"out.json"
            refresh.atomic_json(path,{"ok":True})
            self.assertEqual(json.loads(path.read_text()),{"ok":True})

    def test_range_validation_rejects_bad_values(self):
        with self.assertRaises(ValueError):
            refresh.validate_range([{"lbmp":9999}],"lbmp",-1000,5000)

if __name__ == "__main__": unittest.main()
