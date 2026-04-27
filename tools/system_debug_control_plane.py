from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.system_debug_adapter_registry import build_adapter_registry_artifact, default_adapter_registry
from tools.system_debug_artifact_index import build_artifact_index
from tools.system_debug_manifest import build_system_debug_run_manifest
from tools.system_debug_registry import default_chain_registry, filter_registry
from tools.system_debug_report import build_system_debug_report, write_system_debug_report_files


def run_system_debug_control_plane(
    *,
    artifact_root: str | Path,
    output_dir: str | Path | None = None,
    system_debug_run_id: str | None = None,
    chains: list[str] | None = None,
    explicit_artifacts: list[str | Path] | None = None,
    max_files: int = 5000,
) -> dict[str, str]:
    root = Path(artifact_root)
    output_path = Path(output_dir) if output_dir is not None else root / "system_debug_control_plane"
    output_path.mkdir(parents=True, exist_ok=True)

    registry = filter_registry(default_chain_registry(), selected_names=chains)
    adapter_registry = default_adapter_registry()
    artifact_index = build_artifact_index(
        artifact_root=root,
        chain_registry=registry,
        explicit_artifacts=explicit_artifacts,
        extra_artifact_patterns=_adapter_source_patterns(adapter_registry),
        max_files=max_files,
    )
    manifest = build_system_debug_run_manifest(
        artifact_root=root,
        chain_registry=registry,
        artifact_index=artifact_index,
        system_debug_run_id=system_debug_run_id,
    )
    report = build_system_debug_report(
        manifest=manifest,
        artifact_index=artifact_index,
        chain_registry=registry,
        adapter_registry=adapter_registry,
    )
    adapter_registry_artifact = build_adapter_registry_artifact(
        adapters=adapter_registry,
        resolutions=report.get("adapter_status_matrix") or [],
    )

    artifacts = {
        "system_debug_run_manifest": str(output_path / "system_debug_run_manifest.json"),
        "system_debug_artifact_index": str(output_path / "system_debug_artifact_index.json"),
        "system_debug_adapter_registry": str(output_path / "system_debug_adapter_registry.json"),
    }
    _write_json(output_path / "system_debug_run_manifest.json", manifest)
    _write_json(output_path / "system_debug_artifact_index.json", artifact_index)
    _write_json(output_path / "system_debug_adapter_registry.json", adapter_registry_artifact)
    artifacts.update(write_system_debug_report_files(output_dir=output_path, report=report))
    return artifacts


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a read-only system debug control-plane report.")
    parser.add_argument("--artifact-root", required=True, help="Root directory to scan for existing debug artifacts.")
    parser.add_argument("--output-dir", help="Output directory for system debug control-plane artifacts.")
    parser.add_argument("--system-debug-run-id", help="Optional stable run id.")
    parser.add_argument(
        "--chains",
        help="Optional comma-separated chain names. Defaults to all registered chains.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Optional explicit artifact path. Can be provided multiple times.",
    )
    parser.add_argument("--max-files", type=int, default=5000, help="Maximum files to scan under artifact root.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    selected_chains = [item.strip() for item in args.chains.split(",")] if args.chains else None
    artifacts = run_system_debug_control_plane(
        artifact_root=args.artifact_root,
        output_dir=args.output_dir,
        system_debug_run_id=args.system_debug_run_id,
        chains=selected_chains,
        explicit_artifacts=args.artifact,
        max_files=args.max_files,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))
    return 0


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _adapter_source_patterns(adapter_registry: list[dict[str, Any]]) -> list[str]:
    patterns: list[str] = []
    for adapter in adapter_registry:
        for pattern in adapter.get("source_artifact_patterns") or []:
            text = str(pattern)
            if text and text not in patterns:
                patterns.append(text)
    return patterns


if __name__ == "__main__":
    raise SystemExit(main())
