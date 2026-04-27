import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.system_debug_adapter_registry import (
    build_adapter_registry_artifact,
    default_adapter_registry,
    validate_adapter_registry,
)
from tools.system_debug_adapter_resolution import (
    adapter_coverage_summary,
    missing_required_fields,
    resolve_adapters,
)
from tools.system_debug_artifact_index import build_artifact_index
from tools.system_debug_control_plane import run_system_debug_control_plane
from tools.system_debug_manifest import build_system_debug_run_manifest
from tools.system_debug_registry import default_chain_registry, filter_registry
from tools.system_debug_report import build_system_debug_report


class SystemDebugAdapterRegistryTests(unittest.TestCase):
    def test_adapter_registry_loads_and_exports_contract_statuses(self) -> None:
        adapters = default_adapter_registry()
        self.assertFalse(validate_adapter_registry(adapters))
        artifact = build_adapter_registry_artifact(adapters=adapters)

        self.assertTrue(artifact["read_only"])
        self.assertFalse(artifact["auto_execute"])
        self.assertFalse(artifact["writeback_allowed"])
        self.assertGreaterEqual(artifact["contract_status_counts"].get("explicit", 0), 1)
        self.assertGreaterEqual(artifact["contract_status_counts"].get("inferred", 0), 1)
        self.assertGreaterEqual(artifact["contract_status_counts"].get("manual_only", 0), 1)

    def test_missing_required_fields_strategy_block_warn_degrade_manual_fill(self) -> None:
        payload = {"present": {"field": True}}
        self.assertEqual(missing_required_fields(payload, ["present.field", "missing.field"]), ["missing.field"])

        adapters = [
            self._adapter("block_adapter", "block"),
            self._adapter("warn_adapter", "warn"),
            self._adapter("degrade_adapter", "degrade"),
            self._adapter("manual_adapter", "manual_fill"),
        ]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_json(root / "sample_source.json", payload)
            index = build_artifact_index(
                artifact_root=root,
                chain_registry=[{"chain_name": "source_chain", "artifact_patterns": ["sample_source.json"]}],
            )
            resolutions = resolve_adapters(adapters=adapters, artifact_index=index, chain_reports=[])
            status_by_name = {item["adapter_name"]: item["resolution_status"] for item in resolutions}

            self.assertEqual(status_by_name["block_adapter"], "blocked")
            self.assertEqual(status_by_name["warn_adapter"], "ready_with_warning")
            self.assertEqual(status_by_name["degrade_adapter"], "degraded")
            self.assertEqual(status_by_name["manual_adapter"], "manual_required")

    def test_system_report_shows_inbound_outbound_and_manual_only(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_jsonl(
                root / "source_seed_registry.jsonl",
                {
                    "seed_id": "seed-1",
                    "sample_id": "s1",
                    "source_use": "similar_material",
                    "status": "seed_only",
                    "formalized": False,
                    "verified": False,
                    "verified_original_source": False,
                    "url": "https://example.com/a",
                },
            )
            self._write_json(
                root / "crawl_seed_manifest.json",
                {
                    "crawl_allowed": False,
                    "requires_explicit_crawl_approval": True,
                    "ready_for_material_card_draft": False,
                },
            )
            registry = filter_registry(default_chain_registry(), ["source_discovery_review", "material_protocol_split_pipeline"])
            adapter_registry = default_adapter_registry()
            index = build_artifact_index(artifact_root=root, chain_registry=registry)
            manifest = build_system_debug_run_manifest(
                artifact_root=root,
                chain_registry=registry,
                artifact_index=index,
                system_debug_run_id="adapter-report",
            )
            report = build_system_debug_report(
                manifest=manifest,
                artifact_index=index,
                chain_registry=registry,
                adapter_registry=adapter_registry,
            )

            by_chain = {item["chain_name"]: item for item in report["chains"]}
            self.assertTrue(by_chain["source_discovery_review"]["outbound_adapters"])
            self.assertTrue(by_chain["material_protocol_split_pipeline"]["inbound_adapters"])
            self.assertIn("manual_only_connection_list", report)
            self.assertGreaterEqual(report["adapter_coverage"]["adapter_count"], 1)

    def test_registered_only_chain_is_not_ready_to_connect(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = run_system_debug_control_plane(
                artifact_root=root,
                output_dir=root / "system_debug",
                chains=["difficulty_control_chain"],
            )
            report = json.loads(Path(artifacts["system_debug_report"]).read_text(encoding="utf-8"))

            self.assertEqual(report["chains"][0]["current_status"], "registered_only")
            self.assertFalse(report["chains"][0]["ready_to_connect"])

    def test_control_plane_writes_adapter_registry_artifact(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_jsonl(
                root / "gold_reconstruction_results.jsonl",
                {
                    "sample_id": "s1",
                    "reconstruction_summary": {"confidence": "high", "needs_human_review": False},
                    "gold_material": {},
                    "gold_question": {},
                },
            )
            artifacts = run_system_debug_control_plane(artifact_root=root, output_dir=root / "system_debug")

            adapter_path = Path(artifacts["system_debug_adapter_registry"])
            self.assertTrue(adapter_path.exists())
            adapter_artifact = json.loads(adapter_path.read_text(encoding="utf-8"))
            self.assertIn("adapters", adapter_artifact)
            self.assertIn("resolutions", adapter_artifact)
            coverage = adapter_coverage_summary(adapter_artifact["resolutions"])
            self.assertEqual(coverage["adapter_count"], adapter_artifact["adapter_count"])

    @staticmethod
    def _adapter(name: str, strategy: str) -> dict:
        return {
            "adapter_name": name,
            "source_chain": "source_chain",
            "source_artifact_role": "sample_source",
            "source_artifact_patterns": ["sample_source.json"],
            "target_chain": "target_chain",
            "target_input_role": "target_input",
            "required_fields": ["present.field", "missing.field"],
            "optional_fields": [],
            "missing_field_strategy": strategy,
            "manual_path_allowed": True,
            "contract_status": "inferred",
            "notes": "test adapter",
        }

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_jsonl(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
