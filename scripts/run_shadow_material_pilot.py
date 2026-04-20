from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


ROOT = Path(__file__).resolve().parents[1]
PASSAGE_ROOT = ROOT / "passage_service"
CONFIG_PATH = PASSAGE_ROOT / "app" / "config" / "shadow_material_pilot.yaml"
DEFAULT_SHADOW_ENV = PASSAGE_ROOT / ".env.dev"
DEFAULT_LEGACY_ENV = PASSAGE_ROOT / ".env"
REPORTS_ROOT = ROOT / "reports" / "shadow_pilot"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small-batch shadow material pilot.")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--shadow-env-file", type=Path, default=DEFAULT_SHADOW_ENV)
    parser.add_argument("--legacy-env-file", type=Path, default=DEFAULT_LEGACY_ENV)
    parser.add_argument("--article-limit-override", type=int, default=None)
    parser.add_argument("--skip-crawl", action="store_true")
    parser.add_argument("--skip-compare", action="store_true")
    parser.add_argument("--report-path", type=Path, default=None)
    return parser.parse_args()


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_env_file(path: Path) -> dict[str, str]:
    env_map: dict[str, str] = {}
    if not path.exists():
        return env_map
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        env_map[name.strip()] = value.strip().strip("\"'")
    return env_map


def _apply_env_file(path: Path) -> None:
    for name, value in _load_env_file(path).items():
        os.environ[name] = value


def _resolve_database_url(env_path: Path, default_name: str) -> str:
    env_map = _load_env_file(env_path)
    raw = env_map.get("PASSAGE_DATABASE_URL", f"sqlite:///./{default_name}")
    if not raw.startswith("sqlite:///"):
        return raw
    suffix = raw[len("sqlite:///") :]
    db_path = Path(suffix)
    if not db_path.is_absolute():
        db_path = (PASSAGE_ROOT / db_path).resolve()
    return f"sqlite:///{db_path.as_posix()}"


def _build_engine(database_url: str):
    kwargs: dict[str, Any] = {"future": True}
    if database_url.startswith("sqlite:///"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    return create_engine(database_url, **kwargs)


def _build_session_factory(database_url: str):
    engine = _build_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def _ensure_passage_imports(shadow_database_url: str, shadow_env_file: Path) -> None:
    if str(PASSAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PASSAGE_ROOT))
    os.chdir(PASSAGE_ROOT)
    os.environ["PASSAGE_ENV_FILE"] = str(shadow_env_file.resolve())
    _apply_env_file(shadow_env_file)
    os.environ["PASSAGE_DATABASE_URL"] = shadow_database_url
    os.environ["PASSAGE_ALLOW_NON_PRIMARY_DATABASE"] = "true"


def _apply_crawl_article_limit_override(
    source_ids: list[str],
    article_limit: int | None,
    source_article_limits: dict[str, int] | None = None,
) -> None:
    from app.core.config import get_config_bundle

    normalized_map = {str(key): int(value) for key, value in (source_article_limits or {}).items()}
    for source in get_config_bundle().sources.get("sources", []):
        source_id = str(source.get("id") or "")
        if source_id in normalized_map:
            source["article_limit"] = normalized_map[source_id]
        elif article_limit is not None and source_id in source_ids:
            source["article_limit"] = int(article_limit)


def _excerpt(text: str, limit: int = 110) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def _pick_item_summary(result: dict[str, Any]) -> dict[str, Any]:
    items = result.get("items") or []
    if not items:
        return {"hit": False}
    item = items[0]
    question_ready_context = dict(item.get("question_ready_context") or {})
    source = dict(item.get("source") or {})
    return {
        "hit": True,
        "article_id": item.get("article_id"),
        "material_id": item.get("candidate_id") or item.get("material_id"),
        "title": item.get("article_title") or source.get("article_title"),
        "source_name": source.get("source_name") or source.get("source_id"),
        "source_url": source.get("source_url"),
        "bridge_origin": item.get("bridge_origin"),
        "selected_business_card": question_ready_context.get("selected_business_card"),
        "selected_material_card": question_ready_context.get("selected_material_card"),
        "text_excerpt": _excerpt(item.get("text") or item.get("consumable_text") or ""),
        "quality_score": round(float(item.get("quality_score") or 0.0), 4),
    }


def _render_markdown(
    *,
    config: dict[str, Any],
    crawl_results: list[dict[str, Any]],
    precompute_result: dict[str, Any],
    comparisons: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# Shadow Pilot Report")
    lines.append("")
    lines.append(f"Generated at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("## Pilot Sources")
    lines.append("")
    for source_id in config.get("pilot_sources") or []:
        lines.append(f"- `{source_id}`")
    lines.append("")
    lines.append("## Crawl Summary")
    lines.append("")
    if not crawl_results:
        lines.append("- Crawl was skipped.")
    else:
        for result in crawl_results:
            lines.append(
                f"- `{result.get('source_id')}`: discovered={result.get('discovered_count', 0)}, "
                f"candidate={result.get('candidate_count', 0)}, ingested={result.get('ingested_count', 0)}, "
                f"processed={result.get('processed_count', 0)}, failed={result.get('failed_count', 0)}"
            )
    lines.append("")
    lines.append("## Precompute")
    lines.append("")
    if precompute_result:
        lines.append(f"- index_version: `{precompute_result.get('index_version')}`")
        lines.append(f"- updated_count: `{precompute_result.get('updated_count')}`")
        lines.append(f"- families: `{json.dumps(precompute_result.get('families') or {}, ensure_ascii=False)}`")
    else:
        lines.append("- No precompute result.")
    lines.append("")
    if comparisons:
        lines.append("## Dual Read")
        lines.append("")
        for comparison in comparisons:
            lines.append(f"### {comparison['label']}")
            lines.append("")
            payload = comparison["payload"]
            lines.append(f"- family: `{payload.get('business_family_id')}`")
            lines.append(f"- query_terms: `{', '.join(payload.get('query_terms') or [])}`")
            lines.append("")
            legacy = comparison["legacy"]
            shadow = comparison["shadow"]
            if legacy.get("hit"):
                lines.append(f"- legacy title: {legacy.get('title') or 'N/A'}")
                lines.append(f"- legacy source: {legacy.get('source_name') or 'N/A'}")
                lines.append(f"- legacy card: `{legacy.get('selected_business_card') or ''}`")
                lines.append(f"- legacy excerpt: {legacy.get('text_excerpt') or ''}")
            else:
                lines.append("- legacy title: no hit")
            lines.append("")
            if shadow.get("hit"):
                lines.append(f"- shadow title: {shadow.get('title') or 'N/A'}")
                lines.append(f"- shadow source: {shadow.get('source_name') or 'N/A'}")
                lines.append(f"- shadow card: `{shadow.get('selected_business_card') or ''}`")
                lines.append(f"- shadow excerpt: {shadow.get('text_excerpt') or ''}")
            else:
                lines.append("- shadow title: no hit")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    args = parse_args()
    config = _load_yaml(args.config)
    shadow_database_url = _resolve_database_url(args.shadow_env_file, "passage_service.dev.db")
    legacy_database_url = _resolve_database_url(args.legacy_env_file, "passage_service.db")

    _ensure_passage_imports(shadow_database_url, args.shadow_env_file)

    from app.domain.services.ingest_service import run_crawl_for_source
    from app.domain.services.material_v2_index_service import MaterialV2IndexService
    from app.domain.services.material_pipeline_v2_service import MaterialPipelineV2Service
    from app.infra.db.orm.article import ArticleORM
    from app.infra.db.orm.material_span import MaterialSpanORM
    from app.infra.db.session import init_db

    _apply_crawl_article_limit_override(
        [str(source_id) for source_id in (config.get("pilot_sources") or [])],
        args.article_limit_override,
        config.get("source_article_limits") or {},
    )

    init_db()

    shadow_session_factory = _build_session_factory(shadow_database_url)
    legacy_session_factory = _build_session_factory(legacy_database_url)

    crawl_results: list[dict[str, Any]] = []
    processed_article_ids: list[str] = []
    precompute_result: dict[str, Any] = {}

    if not args.skip_crawl:
        with shadow_session_factory() as shadow_session:
            for source_id in config.get("pilot_sources") or []:
                result = run_crawl_for_source(shadow_session, source_id)
                crawl_results.append(result)
                processed_article_ids.extend(result.get("processed_article_ids") or [])
                shadow_session.commit()
            if processed_article_ids:
                precompute_result = MaterialV2IndexService(shadow_session).precompute(
                    {
                        "article_ids": list(dict.fromkeys(processed_article_ids)),
                        "primary_only": True,
                    }
                )
                shadow_session.commit()

    comparisons: list[dict[str, Any]] = []
    if not args.skip_compare:
        with legacy_session_factory() as legacy_session, shadow_session_factory() as shadow_session:
            legacy_service = MaterialPipelineV2Service(legacy_session)
            shadow_service = MaterialPipelineV2Service(shadow_session)
            for query in config.get("dual_read_queries") or []:
                payload = {
                    "business_family_id": query["business_family_id"],
                    "query_terms": list(query.get("query_terms") or []),
                    "topic": query.get("topic"),
                    "document_genre": query.get("document_genre"),
                    "candidate_limit": int(query.get("candidate_limit", 3)),
                    "article_limit": int(query.get("article_limit", 8)),
                    "review_gate_mode": str(query.get("review_gate_mode") or "stable_relaxed"),
                    "status": "promoted",
                    "release_channel": "stable",
                }
                legacy_result = legacy_service.search(payload)
                shadow_result = shadow_service.search(payload)
                comparisons.append(
                    {
                        "id": query["id"],
                        "label": query["label"],
                        "payload": payload,
                        "legacy": _pick_item_summary(legacy_result),
                        "shadow": _pick_item_summary(shadow_result),
                    }
                )

    report_path = args.report_path or (REPORTS_ROOT / f"shadow_pilot_dual_read_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_text = _render_markdown(
        config=config,
        crawl_results=crawl_results,
        precompute_result=precompute_result,
        comparisons=comparisons,
    )
    report_path.write_text(report_text, encoding="utf-8")

    summary = {
        "report_path": str(report_path),
        "article_limit_override": args.article_limit_override,
        "crawl_results": crawl_results,
        "precompute_result": precompute_result,
        "comparisons": comparisons,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
