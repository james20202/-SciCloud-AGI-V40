import tempfile
import unittest
from pathlib import Path

from core.production_diagnostics import run_diagnostics


class ProductionDiagnosticsTests(unittest.TestCase):
    def test_reports_missing_tools_and_unavailable_local_services(self):
        with tempfile.TemporaryDirectory() as root:
            report = run_diagnostics(
                base_dir=root,
                which=lambda name: None,
                http_check=lambda url: {"ok": False, "message": "connection refused"},
            )
        self.assertEqual(report["mode"], "read_only_local")
        self.assertFalse(report["summary"]["ready"])
        self.assertFalse(report["tools"]["ffmpeg"]["ok"])
        self.assertFalse(report["services"]["ollama"]["ok"])
        self.assertTrue(report["directories"]["output"]["ok"])

    def test_reports_local_tools_and_services_as_available(self):
        with tempfile.TemporaryDirectory() as root:
            report = run_diagnostics(
                base_dir=root,
                which=lambda name: "/usr/bin/" + name,
                http_check=lambda url: {"ok": True, "status_code": 200, "message": "ok"},
            )
        self.assertTrue(report["summary"]["ready"])
        self.assertEqual(report["summary"]["failed"], 0)
        self.assertTrue(report["services"]["comfyui"]["ok"])

    def test_directory_failure_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as root:
            file_path = Path(root) / "not-a-directory"
            file_path.write_text("file", encoding="utf-8")
            report = run_diagnostics(
                base_dir=str(file_path),
                which=lambda name: None,
                http_check=lambda url: {"ok": False, "message": "offline"},
            )
        self.assertTrue(all(not v["ok"] for v in report["directories"].values()))


if __name__ == "__main__":
    unittest.main()
