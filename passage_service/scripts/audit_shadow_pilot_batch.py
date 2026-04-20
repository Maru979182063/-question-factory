from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.infra.db.orm.article import ArticleORM  # noqa: E402
from app.infra.db.orm.audit import AuditEventORM  # noqa: E402
from app.infra.db.orm.candidate_span import CandidateSpanORM  # noqa: E402
from app.infra.db.orm.material_span import MaterialSpanORM  # noqa: E402
from app.infra.db.session import get_session, init_db  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit a shadow pilot batch for manual reading.")
    parser.add_argument("--article-limit", type=int, default=80)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    return parser.parse_args()


def _preview(text: str | None, limit: int = 260) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def _report(article_limit: int) -> dict[str, Any]:
    init_db()
    session = get_session()
    try:
        articles = list(session.scalars(select(ArticleORM).order_by(ArticleORM.created_at.desc()).limit(article_limit)))
        article_ids = [str(article.id) for article in articles]
        candidates = list(session.scalars(select(CandidateSpanORM).where(CandidateSpanORM.article_id.in_(article_ids))))
        materials = list(session.scalars(select(MaterialSpanORM).where(MaterialSpanORM.article_id.in_(article_ids))))
        audits = list(
            session.scalars(
                select(AuditEventORM)
                .where(
                    (
                        (AuditEventORM.entity_type == "article") & (AuditEventORM.entity_id.in_(article_ids))
                    )
                    | (
                        (AuditEventORM.entity_type == "candidate_span")
                        & (AuditEventORM.entity_id.in_([str(item.id) for item in candidates]))
                    )
                    | (
                        (AuditEventORM.entity_type == "material")
                        & (AuditEventORM.entity_id.in_([str(item.id) for item in materials]))
                    )
                )
                .order_by(AuditEventORM.created_at.desc())
            )
        )

        candidates_by_article: dict[str, list[CandidateSpanORM]] = defaultdict(list)
        for item in candidates:
            candidates_by_article[str(item.article_id)].append(item)

        materials_by_article: dict[str, list[MaterialSpanORM]] = defaultdict(list)
        for item in materials:
            materials_by_article[str(item.article_id)].append(item)

        candidate_ids = {str(item.id): str(item.article_id) for item in candidates}
        candidate_reasons_by_article: dict[str, Counter[str]] = defaultdict(Counter)
        article_actions_by_article: dict[str, Counter[str]] = defaultdict(Counter)
        for event in audits:
            payload = dict(event.payload or {})
            if event.entity_type == "candidate_span":
                article_id = candidate_ids.get(str(event.entity_id))
                if not article_id:
                    continue
                reason = (
                    str(payload.get("reject_reason") or "")
                    or str(payload.get("hold_reason") or "")
                    or str(payload.get("result") or "")
                )
                if reason:
                    candidate_reasons_by_article[article_id][reason] += 1
            elif event.entity_type == "article":
                article_actions_by_article[str(event.entity_id)][str(event.action)] += 1

        rows: list[dict[str, Any]] = []
        source_counts = Counter()
        status_counts = Counter()
        for article in articles:
            article_id = str(article.id)
            article_candidates = candidates_by_article.get(article_id, [])
            article_materials = materials_by_article.get(article_id, [])
            source_counts[str(article.source or "")] += 1
            status_counts[str(article.status or "")] += 1
            rows.append(
                {
                    "article_id": article_id,
                    "source": str(article.source or ""),
                    "status": str(article.status or ""),
                    "title": str(article.title or ""),
                    "source_url": str(article.source_url or ""),
                    "body_preview": _preview(article.clean_text, 420),
                    "candidate_count": len(article_candidates),
                    "candidate_status_counts": dict(Counter(str(item.status or "") for item in article_candidates)),
                    "material_count": len(article_materials),
                    "material_status_counts": dict(
                        Counter(f"{item.status}/{item.release_channel}" for item in article_materials)
                    ),
                    "top_candidate_reasons": dict(candidate_reasons_by_article.get(article_id, Counter()).most_common(8)),
                    "article_actions": dict(article_actions_by_article.get(article_id, Counter())),
                    "material_samples": [
                        {
                            "material_id": str(item.id),
                            "primary_family": str(item.primary_family or ""),
                            "primary_label": str(item.primary_label or ""),
                            "v2_business_family_ids": [str(fam) for fam in (item.v2_business_family_ids or [])],
                            "v2_index_version": str(item.v2_index_version or ""),
                            "text_preview": _preview(item.text, 220),
                        }
                        for item in article_materials[:3]
                    ],
                    "candidate_samples": [
                        {
                            "candidate_id": str(item.id),
                            "span_type": str(item.span_type or ""),
                            "status": str(item.status or ""),
                            "text_preview": _preview(item.text, 180),
                        }
                        for item in article_candidates[:4]
                    ],
                }
            )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "article_limit": article_limit,
            "article_count": len(rows),
            "source_counts": dict(source_counts),
            "status_counts": dict(status_counts),
            "articles": rows,
        }
    finally:
        session.close()


def _to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Shadow Pilot Batch Audit",
        "",
        f"- article_limit: {report.get('article_limit', 0)}",
        f"- article_count: {report.get('article_count', 0)}",
        f"- source_counts: {report.get('source_counts', {})}",
        f"- status_counts: {report.get('status_counts', {})}",
        "",
        "## Articles",
    ]
    for row in report.get("articles", []):
        lines.extend(
            [
                f"### {row['title'] or row['article_id']}",
                "",
                f"- article_id: `{row['article_id']}`",
                f"- source: `{row['source']}`",
                f"- status: `{row['status']}`",
                f"- candidate_count: `{row['candidate_count']}`",
                f"- candidate_status_counts: `{row['candidate_status_counts']}`",
                f"- material_count: `{row['material_count']}`",
                f"- material_status_counts: `{row['material_status_counts']}`",
                f"- top_candidate_reasons: `{row['top_candidate_reasons']}`",
                f"- source_url: {row['source_url']}",
                f"- body_preview: {row['body_preview']}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    report = _report(article_limit=args.article_limit)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.write_text(_to_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
