from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - fallback for lean environments
    yaml = None


ALLOWED_WRITE_TARGETS = {"business_feature_card", "signal_layer", "validator_contract"}

ALLOWLIST_PATH_PREFIXES = {
    "business_feature_card": Path("card_specs/business_feature_slots/examples"),
    "signal_layer": Path("card_specs/normalized/signal_layers"),
    "validator_contract": Path("card_specs/validator_contracts/proto"),
}

SHARED_CONFIG_TARGETS = {
    "prompt_assets",
    "material_mapping",
    "runtime_mapping",
    "material_card",
    "question_card",
}


class FormalWritebackError(ValueError):
    pass


def load_writeback_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_writeback_approval(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def execute_formal_writeback(
    *,
    plan: dict[str, Any],
    approval: dict[str, Any] | None,
    repo_root: str | Path,
    output_dir: str | Path,
    regression_commands: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    approved_items = validate_writeback_approval(plan=plan, approval=approval, repo_root=root)
    rendered_files = render_writeback_files(plan=plan, items=approved_items)
    snapshots = _build_file_snapshots(root=root, rendered_files=rendered_files)
    forward_patch = _render_patch(snapshots, reverse=False)
    rollback_patch = _render_patch(snapshots, reverse=True)

    forward_patch_path = out / "formal_writeback_forward.patch"
    rollback_patch_path = out / "formal_writeback_rollback.patch"
    forward_patch_path.write_text(forward_patch, encoding="utf-8")
    rollback_patch_path.write_text(rollback_patch, encoding="utf-8")

    if not dry_run:
        for snapshot in snapshots:
            target_path = root / snapshot["path"]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(snapshot["after_text"], encoding="utf-8", newline="\n")
        _verify_after_hashes(root=root, snapshots=snapshots)

    regression_report = run_writeback_regressions(regression_commands or [])
    regression_path = out / "formal_writeback_regression_report.json"
    regression_path.write_text(json.dumps(regression_report, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "manifest_version": "v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "formal_writeback_executor",
        "status": "dry_run" if dry_run else ("succeeded" if regression_report["passed"] else "failed_regression"),
        "dry_run": dry_run,
        "proto_family": plan.get("proto_family"),
        "proto_child_family": plan.get("proto_child_family"),
        "approved_by": approval.get("approved_by") if approval else None,
        "writeback_targets": [item.get("target") for item in approved_items],
        "files": [
            {
                "path": snapshot["path"],
                "before_sha256": snapshot["before_sha256"],
                "after_sha256": snapshot["after_sha256"],
                "created_new_file": snapshot["created_new_file"],
            }
            for snapshot in snapshots
        ],
        "forward_patch_path": str(forward_patch_path),
        "rollback_patch_path": str(rollback_patch_path),
        "regression_report_path": str(regression_path),
        "rollback_command": f"git apply {rollback_patch_path}",
        "limits": [
            "Only Executor v1 allowlist proto files were written.",
            "Shared config targets are rejected.",
            "Prompt, generation, and validator main logic are not modified by this executor.",
        ],
    }
    manifest_path = out / "formal_writeback_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": manifest["status"],
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "forward_patch_path": str(forward_patch_path),
        "rollback_patch_path": str(rollback_patch_path),
        "regression_report_path": str(regression_path),
    }


def validate_writeback_approval(
    *,
    plan: dict[str, Any],
    approval: dict[str, Any] | None,
    repo_root: str | Path,
) -> list[dict[str, Any]]:
    if approval is None:
        raise FormalWritebackError("formal writeback approval is required.")
    if not isinstance(approval, dict):
        raise FormalWritebackError("formal writeback approval must be a JSON object.")
    if approval.get("approval_version") != "v1":
        raise FormalWritebackError("approval_version must be v1.")
    if approval.get("approval_type") != "formal_writeback":
        raise FormalWritebackError("approval_type must be formal_writeback.")
    if approval.get("approved") is not True:
        raise FormalWritebackError("approval must set approved=true.")
    if not approval.get("approved_at"):
        raise FormalWritebackError("approval must include approved_at.")
    approved_by = str(approval.get("approved_by") or "").strip()
    if not approved_by or approved_by.lower() in {"llm", "model", "auto", "system"}:
        raise FormalWritebackError("approval must include a human approved_by value.")

    scope = approval.get("approval_scope")
    if not isinstance(scope, dict):
        raise FormalWritebackError("approval_scope is required.")
    _require_equal(scope.get("proto_family"), plan.get("proto_family"), "approval_scope.proto_family")
    _require_equal(scope.get("proto_child_family"), plan.get("proto_child_family"), "approval_scope.proto_child_family")
    allowed_targets = scope.get("allowed_targets")
    allowed_files = scope.get("allowed_files")
    if not isinstance(allowed_targets, list) or not allowed_targets:
        raise FormalWritebackError("approval_scope.allowed_targets must be a non-empty list.")
    if not isinstance(allowed_files, list) or not allowed_files:
        raise FormalWritebackError("approval_scope.allowed_files must be a non-empty list.")
    if set(allowed_targets) & SHARED_CONFIG_TARGETS:
        raise FormalWritebackError("shared config target is not executable in v1.")
    if not set(allowed_targets).issubset(ALLOWED_WRITE_TARGETS):
        raise FormalWritebackError("approval includes targets outside Executor v1 allowlist.")

    source_artifacts = approval.get("source_artifacts")
    if not isinstance(source_artifacts, dict) or not source_artifacts.get("formal_writeback_plan_path"):
        raise FormalWritebackError("approval.source_artifacts.formal_writeback_plan_path is required.")

    assertions = approval.get("human_review_assertions")
    required_assertions = [
        "candidate_axes_are_proto_confirmed",
        "draft_reviewed",
        "diff_reviewed",
        "rollback_reviewed",
        "no_shared_config_write_in_v1",
    ]
    if not isinstance(assertions, dict) or any(assertions.get(key) is not True for key in required_assertions):
        raise FormalWritebackError("approval human_review_assertions are incomplete.")

    if plan.get("status") != "preview_only":
        raise FormalWritebackError("formal_writeback_plan.status must be preview_only.")
    if plan.get("writeback_allowed") is not False:
        raise FormalWritebackError("formal_writeback_plan.writeback_allowed must remain false.")
    if plan.get("requires_explicit_approval") is not True:
        raise FormalWritebackError("formal_writeback_plan.requires_explicit_approval must be true.")

    items = plan.get("writeback_items")
    if not isinstance(items, list) or not items:
        raise FormalWritebackError("formal_writeback_plan.writeback_items must be non-empty.")

    selected_items = []
    for item in items:
        if not isinstance(item, dict):
            raise FormalWritebackError("writeback item must be an object.")
        target = item.get("target")
        if target in SHARED_CONFIG_TARGETS or item.get("shared_config_touch"):
            raise FormalWritebackError(f"shared config target is not executable in v1: {target}")
        if target not in ALLOWED_WRITE_TARGETS:
            raise FormalWritebackError(f"target is not executable in v1: {target}")
        if target not in allowed_targets:
            continue
        if item.get("writeback_allowed") is not False:
            raise FormalWritebackError("writeback item writeback_allowed must remain false.")
        if item.get("requires_explicit_approval") is not True:
            raise FormalWritebackError("writeback item requires_explicit_approval must be true.")
        target_file = str(item.get("target_file") or "")
        if target_file not in allowed_files:
            raise FormalWritebackError(f"target_file is not approved: {target_file}")
        _validate_target_path(target=target, target_file=target_file, repo_root=Path(repo_root))
        selected_items.append(item)

    if not selected_items:
        raise FormalWritebackError("approval did not select any executable writeback items.")

    selected_files = {str(item.get("target_file") or "") for item in selected_items}
    if selected_files != set(allowed_files):
        raise FormalWritebackError("approval_scope.allowed_files must exactly match selected writeback files.")

    return selected_items


def render_writeback_files(*, plan: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, str]:
    rendered: dict[str, str] = {}
    for item in items:
        payload = _proto_payload(plan=plan, item=item)
        rendered[str(item["target_file"])] = _dump_yaml(payload)
    return rendered


def run_writeback_regressions(commands: list[str]) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    results = []
    for command in commands:
        completed = subprocess.run(command, shell=True, text=True, capture_output=True)
        results.append(
            {
                "command": command,
                "exit_code": completed.returncode,
                "passed": completed.returncode == 0,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        )
    finished = datetime.now(timezone.utc)
    return {
        "report_version": "v1",
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "passed": bool(commands) and all(item["passed"] for item in results),
        "command_count": len(commands),
        "results": results,
    }


def _proto_payload(*, plan: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "formal_writeback_proto_artifact.v1",
        "experimental": True,
        "formalized": False,
        "source": "formal_writeback_executor",
        "target": item.get("target"),
        "scope_key": item.get("scope_key"),
        "proto_family": plan.get("proto_family"),
        "proto_child_family": plan.get("proto_child_family"),
        "leaf_label": plan.get("leaf_label"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "proposed_additions": item.get("proposed_additions") or [],
        "prompt_guards": item.get("prompt_guards") or [],
        "validator_candidates": item.get("validator_candidates") or [],
        "rollback": item.get("rollback"),
        "limits": [
            "This proto file was generated from a human-approved formal_writeback_plan.",
            "It remains experimental and formalized=false.",
            "It must not be treated as stable card_specs without a later promotion step.",
        ],
    }


def _build_file_snapshots(*, root: Path, rendered_files: dict[str, str]) -> list[dict[str, Any]]:
    snapshots = []
    for relative_path, after_text in sorted(rendered_files.items()):
        path = root / relative_path
        if path.exists():
            raise FormalWritebackError(f"Executor v1 refuses to overwrite existing file: {relative_path}")
        before_text = ""
        snapshots.append(
            {
                "path": relative_path.replace("\\", "/"),
                "before_text": before_text,
                "after_text": after_text,
                "before_sha256": _sha256(before_text),
                "after_sha256": _sha256(after_text),
                "created_new_file": True,
            }
        )
    return snapshots


def _verify_after_hashes(*, root: Path, snapshots: list[dict[str, Any]]) -> None:
    for snapshot in snapshots:
        path = root / snapshot["path"]
        actual = path.read_text(encoding="utf-8")
        if _sha256(actual) != snapshot["after_sha256"]:
            raise FormalWritebackError(f"after hash verification failed for {snapshot['path']}")


def _render_patch(snapshots: list[dict[str, Any]], *, reverse: bool) -> str:
    chunks: list[str] = []
    for snapshot in snapshots:
        path = snapshot["path"]
        before_text = snapshot["after_text"] if reverse else snapshot["before_text"]
        after_text = snapshot["before_text"] if reverse else snapshot["after_text"]
        fromfile = f"a/{path}"
        tofile = f"b/{path}"
        chunks.append(f"diff --git a/{path} b/{path}")
        chunks.append("deleted file mode 100644" if reverse else "new file mode 100644")
        chunks.extend(
            difflib.unified_diff(
                before_text.splitlines(keepends=True),
                after_text.splitlines(keepends=True),
                fromfile=fromfile if not reverse else fromfile,
                tofile=tofile if not reverse else "/dev/null",
                lineterm="",
            )
        )
        chunks.append("")
    return "\n".join(chunks)


def _validate_target_path(*, target: str, target_file: str, repo_root: Path) -> None:
    relative = Path(target_file)
    if relative.is_absolute():
        raise FormalWritebackError(f"target_file must be relative: {target_file}")
    resolved = (repo_root / relative).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise FormalWritebackError(f"target_file escapes repo root: {target_file}") from exc

    prefix = ALLOWLIST_PATH_PREFIXES[target]
    try:
        relative.relative_to(prefix)
    except ValueError as exc:
        raise FormalWritebackError(f"target_file is outside allowlist for {target}: {target_file}") from exc
    name = relative.name
    if target == "business_feature_card" and not name.endswith(".proto.yaml"):
        raise FormalWritebackError("business_feature_card writeback must use .proto.yaml.")
    if target == "signal_layer" and not name.endswith("_signal_layer.proto.yaml"):
        raise FormalWritebackError("signal_layer writeback must use *_signal_layer.proto.yaml.")
    if target == "validator_contract" and not name.endswith(".validator.yaml"):
        raise FormalWritebackError("validator_contract writeback must use .validator.yaml.")


def _require_equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise FormalWritebackError(f"{field} does not match formal_writeback_plan.")


def _dump_yaml(payload: dict[str, Any]) -> str:
    if yaml is not None:
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute an approved formal writeback plan.")
    parser.add_argument("--formal-writeback-plan", required=True)
    parser.add_argument("--formal-writeback-approval", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--regression-command", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = execute_formal_writeback(
        plan=load_writeback_plan(args.formal_writeback_plan),
        approval=load_writeback_approval(args.formal_writeback_approval),
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        regression_commands=args.regression_command,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
