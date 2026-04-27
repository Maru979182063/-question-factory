import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.system_debug_artifact_index import build_artifact_index
from tools.system_debug_control_plane import run_system_debug_control_plane
from tools.system_debug_registry import default_chain_registry, filter_registry
from tools.system_debug_report import build_system_debug_report
from tools.system_debug_manifest import build_system_debug_run_manifest


class SystemDebugControlPlaneTests(unittest.TestCase):
    def test_control_plane_generates_required_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_json(root / "pipeline_state.json", self._pipeline_state("success"))
            self._write_json(root / "pipeline_stage_report.json", {"pipeline_complete": True, "blocked": False, "status_counts": {"success": 6}})
            self._write_json(root / "source_candidate_review.json", {"status": "reviewed", "verified_original_source_count": 0})

            output_dir = root / "system_debug"
            artifacts = run_system_debug_control_plane(
                artifact_root=root,
                output_dir=output_dir,
                system_debug_run_id="debug-test",
            )

            self.assertTrue(Path(artifacts["system_debug_run_manifest"]).exists())
            self.assertTrue(Path(artifacts["system_debug_artifact_index"]).exists())
            self.assertTrue(Path(artifacts["system_debug_report"]).exists())
            self.assertTrue(Path(artifacts["system_debug_report_md"]).exists())

            report = json.loads(Path(artifacts["system_debug_report"]).read_text(encoding="utf-8"))
            self.assertTrue(report["read_only"])
            self.assertFalse(report["auto_execute"])
            self.assertFalse(report["llm_calls_made"])
            self.assertFalse(report["writeback_allowed"])
            self.assertGreaterEqual(report["summary"]["registered_chain_count"], 1)

    def test_blocked_stage_is_reported_as_blocked_chain(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_json(root / "pipeline_state.json", self._pipeline_state("provider_error"))
            registry = filter_registry(default_chain_registry(), ["material_protocol_split_pipeline"])
            index = build_artifact_index(artifact_root=root, chain_registry=registry)
            manifest = build_system_debug_run_manifest(
                artifact_root=root,
                chain_registry=registry,
                artifact_index=index,
                system_debug_run_id="debug-blocked",
            )
            report = build_system_debug_report(manifest=manifest, artifact_index=index, chain_registry=registry)

            self.assertEqual(report["summary"]["blocked_chain_count"], 1)
            self.assertEqual(report["chains"][0]["current_status"], "blocked")
            self.assertIn("stage error", report["chains"][0]["status_reason"])

    def test_registered_chain_without_artifact_stays_registered_only(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = filter_registry(default_chain_registry(), ["difficulty_control_chain"])
            artifacts = run_system_debug_control_plane(
                artifact_root=root,
                output_dir=root / "system_debug",
                chains=["difficulty_control_chain"],
            )
            report = json.loads(Path(artifacts["system_debug_report"]).read_text(encoding="utf-8"))

            self.assertEqual(report["summary"]["registered_only_chain_count"], 1)
            self.assertEqual(report["chains"][0]["current_status"], "registered_only")
            self.assertEqual(report["chains"][0]["artifact_count"], 0)

    def test_dependency_edges_are_recorded_without_execution(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = run_system_debug_control_plane(
                artifact_root=root,
                output_dir=root / "system_debug",
                chains=["distillation_runtime_workbench"],
            )
            manifest = json.loads(Path(artifacts["system_debug_run_manifest"]).read_text(encoding="utf-8"))

            self.assertFalse(manifest["auto_execute"])
            self.assertFalse(manifest["llm_calls_allowed"])
            self.assertFalse(manifest["writeback_allowed"])
            self.assertTrue(manifest["dependency_edges"])

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _pipeline_state(status: str) -> dict:
        return {
            "state_version": "v1",
            "mode": "mock",
            "stages": {
                "material_evidence_map": {
                    "stage": "material_evidence_map",
                    "status": status,
                    "output_path": "stages/01_material_evidence_map.json",
                    "retry_count": 1 if status == "provider_error" else 0,
                    "error_summary": "provider HTTP 502" if status == "provider_error" else "",
                }
            },
        }


if __name__ == "__main__":
    unittest.main()

