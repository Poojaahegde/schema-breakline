import json
import tempfile
import unittest
from pathlib import Path

from contract_guard import check_stream, dashboard


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract.json"


class ContractGateTests(unittest.TestCase):
    def test_passing_batch(self):
        report = check_stream(CONTRACT, ROOT / "incoming/latest.jsonl")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["issue_count"], 0)

    def test_breaking_batch_identifies_decision_fields(self):
        report = check_stream(CONTRACT, ROOT / "examples/breaking.jsonl")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["issue_count"], 3)
        self.assertEqual(
            [(item["line"], item["path"], item["rule"]) for item in report["issues"]],
            [(2, "user_id", "type"), (3, "sync_status", "enum"), (4, "invoice_id", "required")],
        )
        self.assertIn("user_id", dashboard(report))

    def test_empty_and_malformed_batches_block(self):
        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "events.jsonl"
            sample.write_text("\n", encoding="utf-8")
            self.assertEqual(check_stream(CONTRACT, sample)["issues"][0]["rule"], "empty")
            sample.write_text('{"event_name":', encoding="utf-8")
            self.assertEqual(check_stream(CONTRACT, sample)["issues"][0]["rule"], "json")

    def test_html_escapes_untrusted_values(self):
        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "events.jsonl"
            event = json.loads((ROOT / "incoming/latest.jsonl").read_text().splitlines()[0])
            event["invoice_id"] = "<script>alert(1)</script>"
            event["sync_status"] = "<script>alert(1)</script>"
            sample.write_text(json.dumps(event) + "\n", encoding="utf-8")
            html = dashboard(check_stream(CONTRACT, sample))
            self.assertNotIn("<script>", html)
            self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
