from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen


DEFAULT_MAX_SAMPLES = 5
DEFAULT_MAX_QUERIES_PER_SAMPLE = 3
DEFAULT_MAX_RESULTS_PER_QUERY = 5
DEFAULT_SEARCH_TIMEOUT_SECONDS = 20

NEGATIVE_TERMS = [
    "题库",
    "答案",
    "解析",
    "试题",
    "真题",
    "模拟题",
    "练习题",
    "刷题",
    "估分",
    "题目",
    "选项",
    "正确答案",
    "参考答案",
    "答案解析",
    "本题考查",
    "下列",
    "正确的是",
    "不正确的是",
    "加点词",
    "公务员考试",
    "国考",
    "省考",
    "联考",
    "行测",
    "职测",
    "事业单位",
    "行政职业能力测验",
    "判断推理",
    "言语理解",
    "片段阅读",
    "逻辑填空",
    "语句排序",
    "中公",
    "华图",
    "粉笔",
    "腰果公考",
    "步知公考",
    "半月谈教育",
    "233网校",
    "考试吧",
    "上岸鸭",
    "公考雷达",
    "公务员考试网",
    "国家公务员考试网",
    "省公务员考试网",
]

DOMAIN_RISK_PATTERNS = [
    "gongwuyuan",
    "guokao",
    "shengkao",
    "xingce",
    "zhice",
    "huatu",
    "offcn",
    "fenbi",
    "233",
    "exam8",
    "eoffcn",
    "zggwy",
    "chinagwy",
    "tiku",
    "shiti",
    "jiex",
    "daan",
    "mock",
    "practice",
]

POSITIVE_SOURCE_HINTS = [
    "people.com.cn",
    "xinhuanet.com",
    "gmw.cn",
    "cctv.com",
    "chinanews.com.cn",
    "china.com.cn",
    "qstheory.cn",
    "cssn.cn",
    "kepuchina.cn",
    ".gov.cn",
    ".edu.cn",
]


class SearchProvider(Protocol):
    name: str

    def search(self, *, query: str, max_results: int, timeout_seconds: int) -> list[dict[str, Any]]:
        ...


class MockSearchProvider:
    name = "mock"

    def search(self, *, query: str, max_results: int, timeout_seconds: int) -> list[dict[str, Any]]:
        digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:10]
        natural_title = truncate_text(strip_query_noise(query), 36) or "source candidate"
        rows = [
            {
                "title": f"来源文章候选：{natural_title}",
                "url": f"https://www.xinhuanet.com/example/{digest}.html",
                "snippet": truncate_text(query, 140),
            },
            {
                "title": f"{natural_title} 公务员考试题库答案解析",
                "url": f"https://www.offcn.com/tiku/{digest}.html",
                "snippet": f"本题考查言语理解，正确答案请查看解析。{truncate_text(query, 60)}",
            },
        ]
        return rows[:max_results]


class ManualSearchProvider:
    name = "manual"

    def search(self, *, query: str, max_results: int, timeout_seconds: int) -> list[dict[str, Any]]:
        return []


class WebSearchProvider:
    name = "web"

    def search(self, *, query: str, max_results: int, timeout_seconds: int) -> list[dict[str, Any]]:
        errors: list[str] = []
        for engine, url, parser in (
            ("duckduckgo", f"https://html.duckduckgo.com/html/?q={quote_plus(query)}", parse_duckduckgo_html_results),
            ("bing", f"https://www.bing.com/search?q={quote_plus(query)}", parse_bing_html_results),
        ):
            try:
                body = fetch_search_html(url=url, timeout_seconds=timeout_seconds)
                results = parser(body)
                if results:
                    return results[:max_results]
                errors.append(f"{engine}: no parseable results")
            except Exception as exc:
                errors.append(f"{engine}: {exc}")
        if errors and all("no parseable results" not in error for error in errors):
            raise RuntimeError(" | ".join(errors))
        return []


def fetch_search_html(*, url: str, timeout_seconds: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 source-candidate-search-v1",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


class DuckDuckGoHTMLResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._active_link = False
        self._active_snippet = False
        self._current: dict[str, str] | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value or "" for key, value in attrs}
        classes = set((attrs_dict.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self._flush_current()
            self._current = {"title": "", "url": normalize_search_result_url(attrs_dict.get("href") or ""), "snippet": ""}
            self._active_link = True
            self._buffer = []
        elif "result__snippet" in classes:
            self._active_snippet = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active_link and self._current is not None:
            self._current["title"] = clean_html_text("".join(self._buffer))
            self._active_link = False
            self._buffer = []
        elif self._active_snippet:
            snippet = clean_html_text("".join(self._buffer))
            if self._current is not None and snippet:
                self._current["snippet"] = snippet
            self._active_snippet = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._active_link or self._active_snippet:
            self._buffer.append(data)

    def close(self) -> None:
        super().close()
        self._flush_current()

    def _flush_current(self) -> None:
        if self._current and self._current.get("title") and self._current.get("url"):
            self.results.append(dict(self._current))
        self._current = None


def parse_duckduckgo_html_results(body: str) -> list[dict[str, str]]:
    parser = DuckDuckGoHTMLResultParser()
    parser.feed(body)
    parser.close()
    return parser.results


def parse_bing_html_results(body: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    blocks = re.findall(r"<li[^>]+class=\"[^\"]*b_algo[^\"]*\"[^>]*>(.*?)</li>", body, flags=re.IGNORECASE | re.DOTALL)
    for block in blocks:
        link = re.search(r"<h2[^>]*>\s*<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", block, flags=re.IGNORECASE | re.DOTALL)
        if not link:
            continue
        snippet_match = re.search(r"<p[^>]*>(.*?)</p>", block, flags=re.IGNORECASE | re.DOTALL)
        results.append(
            {
                "title": clean_html_text(strip_html_tags(link.group(2))),
                "url": html.unescape(link.group(1)),
                "snippet": clean_html_text(strip_html_tags(snippet_match.group(1) if snippet_match else "")),
            }
        )
    return results


def normalize_search_result_url(url: str) -> str:
    value = html.unescape(str(url or "")).strip()
    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    return value


def clean_html_text(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(text or ""))).strip()


def strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", str(text or ""))


def run_source_candidate_search_from_queries(
    *,
    source_discovery_queries_path: str | Path,
    output_dir: str | Path,
    max_samples: int = DEFAULT_MAX_SAMPLES,
    max_queries_per_sample: int = DEFAULT_MAX_QUERIES_PER_SAMPLE,
    max_results_per_query: int = DEFAULT_MAX_RESULTS_PER_QUERY,
    allowed_risk: str = "low",
    dry_run: bool = True,
    run_search: bool = False,
    search_provider: str = "manual",
    search_api_key_env: str = "SOURCE_SEARCH_API_KEY",
    search_timeout_seconds: int = DEFAULT_SEARCH_TIMEOUT_SECONDS,
    provider: SearchProvider | None = None,
) -> dict[str, str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    source_path = Path(source_discovery_queries_path)
    query_rows = load_jsonl(source_path)
    selected = select_source_queries(
        query_rows=query_rows,
        max_samples=max_samples,
        max_queries_per_sample=max_queries_per_sample,
        allowed_risk=allowed_risk,
    )
    effective_run_search = bool(run_search and not dry_run)
    active_provider = provider or build_search_provider(search_provider)
    manifest = build_search_request_manifest(
        source_queries_path=source_path,
        provider_name=search_provider if provider is None else active_provider.name,
        run_search=effective_run_search,
        selected=selected,
        max_samples=max_samples,
        max_queries_per_sample=max_queries_per_sample,
        max_results_per_query=max_results_per_query,
        allowed_risk=allowed_risk,
        search_api_key_env=search_api_key_env,
        timeout_seconds=search_timeout_seconds,
    )

    candidates: list[dict[str, Any]] = []
    provider_error = ""
    if effective_run_search:
        try:
            candidates = collect_candidates(
                selected=selected,
                provider=active_provider,
                max_results_per_query=max_results_per_query,
                timeout_seconds=search_timeout_seconds,
            )
        except Exception as exc:
            provider_error = str(exc)
            manifest["provider_status"] = "provider_unavailable"
            manifest["provider_error"] = provider_error
    else:
        manifest["provider_status"] = "dry_run" if dry_run else "manual_request_only"

    summary = build_source_candidate_summary(
        selected=selected,
        candidates=candidates,
        provider_status=manifest.get("provider_status") or "ok",
    )
    report = render_source_candidate_alignment_report(
        manifest=manifest,
        selected=selected,
        candidates=candidates,
        summary=summary,
    )

    manifest_path = output_path / "search_request_manifest.json"
    results_path = output_path / "source_candidate_results.jsonl"
    summary_path = output_path / "source_candidate_summary.json"
    report_path = output_path / "source_candidate_alignment_report.md"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    write_jsonl(results_path, candidates)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    return {
        "search_request_manifest": str(manifest_path),
        "source_candidate_results": str(results_path),
        "source_candidate_summary": str(summary_path),
        "source_candidate_alignment_report": str(report_path),
    }


def select_source_queries(
    *,
    query_rows: list[dict[str, Any]],
    max_samples: int,
    max_queries_per_sample: int,
    allowed_risk: str,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in query_rows:
        if len(selected) >= max_samples:
            break
        if str(row.get("question_bank_contamination_risk") or "") != allowed_risk:
            continue
        if row.get("needs_human_review"):
            continue
        queries = sorted(
            [
                query
                for query in (row.get("search_queries") or [])
                if query.get("confidence") in {"high", "medium"}
            ],
            key=query_priority,
        )[:max_queries_per_sample]
        if not queries:
            continue
        selected.append(
            {
                "sample_id": row.get("sample_id"),
                "question_bank_contamination_risk": row.get("question_bank_contamination_risk"),
                "needs_human_review": bool(row.get("needs_human_review")),
                "restored_human_material": row.get("restored_human_material") or "",
                "search_queries": queries,
            }
        )
    return selected


def query_priority(query: dict[str, Any]) -> tuple[int, int]:
    purpose_rank = 0 if query.get("purpose") == "find_original_source" else 1
    confidence_rank = 0 if query.get("confidence") == "high" else 1
    return (purpose_rank, confidence_rank)


def build_search_request_manifest(
    *,
    source_queries_path: Path,
    provider_name: str,
    run_search: bool,
    selected: list[dict[str, Any]],
    max_samples: int,
    max_queries_per_sample: int,
    max_results_per_query: int,
    allowed_risk: str,
    search_api_key_env: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    return {
        "search_version": "v1",
        "source_queries_path": str(source_queries_path),
        "provider": provider_name,
        "provider_status": "ok" if run_search else "dry_run",
        "run_search": bool(run_search),
        "selected_sample_ids": [row.get("sample_id") for row in selected],
        "query_count": sum(len(row.get("search_queries") or []) for row in selected),
        "limits": {
            "max_samples": max_samples,
            "max_queries_per_sample": max_queries_per_sample,
            "max_results_per_query": max_results_per_query,
            "allowed_risk": allowed_risk,
            "search_api_key_env": search_api_key_env,
            "timeout_seconds": timeout_seconds,
        },
        "boundaries": [
            "candidate sources are unverified",
            "no original source is confirmed",
            "no material library or material_card write happened",
        ],
    }


def build_search_provider(provider_name: str) -> SearchProvider:
    if provider_name == "mock":
        return MockSearchProvider()
    if provider_name == "manual":
        return ManualSearchProvider()
    if provider_name == "web":
        return WebSearchProvider()
    raise ValueError("search provider must be mock, manual, or web")


def collect_candidates(
    *,
    selected: list[dict[str, Any]],
    provider: SearchProvider,
    max_results_per_query: int,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for sample in selected:
        restored = str(sample.get("restored_human_material") or "")
        for query_row in sample.get("search_queries") or []:
            raw_results = provider.search(
                query=str(query_row.get("query") or ""),
                max_results=max_results_per_query,
                timeout_seconds=timeout_seconds,
            )
            for rank, raw in enumerate(raw_results[:max_results_per_query], start=1):
                candidates.append(
                    normalize_candidate_result(
                        sample_id=str(sample.get("sample_id") or ""),
                        query_row=query_row,
                        restored_human_material=restored,
                        candidate_rank=rank,
                        raw=raw,
                    )
                )
    return candidates


def normalize_candidate_result(
    *,
    sample_id: str,
    query_row: dict[str, Any],
    restored_human_material: str,
    candidate_rank: int,
    raw: dict[str, Any],
) -> dict[str, Any]:
    title = str(raw.get("title") or "")
    url = str(raw.get("url") or "")
    domain = domain_from_url(url)
    snippet = str(raw.get("snippet") or "")
    risk = classify_source_risk(title=title, url=url, domain=domain, snippet=snippet)
    alignment = alignment_signals(
        query=str(query_row.get("query") or ""),
        restored=restored_human_material,
        title=title,
        snippet=snippet,
        source_risk=risk,
        domain=domain,
    )
    score = candidate_score(alignment=alignment, source_risk=risk, domain=domain)
    status = candidate_status(source_risk=risk, score=score)
    warnings = []
    if risk in {"question_bank_like", "exam_training_like"}:
        warnings.append("candidate looks like question bank or exam training source")
    return {
        "sample_id": sample_id,
        "query": query_row.get("query") or "",
        "query_type": query_row.get("query_type") or "",
        "candidate_rank": candidate_rank,
        "title": title,
        "url": url,
        "domain": domain,
        "snippet": snippet,
        "source_risk": risk,
        "candidate_score": round(score, 4),
        "candidate_status": status,
        "verification_status": "unverified",
        "verified": False,
        "alignment_signals": alignment,
        "warnings": warnings,
    }


def classify_source_risk(*, title: str, url: str, domain: str, snippet: str) -> str:
    haystack = f"{title} {url} {domain} {snippet}".lower()
    if any(pattern in haystack for pattern in DOMAIN_RISK_PATTERNS):
        if any(pattern in haystack for pattern in ("huatu", "offcn", "fenbi", "gongwuyuan", "guokao", "xingce", "zhice")):
            return "exam_training_like"
        return "question_bank_like"
    if any(term.lower() in haystack for term in NEGATIVE_TERMS):
        return "question_bank_like"
    if any(hint in domain.lower() or hint in url.lower() for hint in POSITIVE_SOURCE_HINTS):
        return "low"
    return "unknown"


def alignment_signals(
    *,
    query: str,
    restored: str,
    title: str,
    snippet: str,
    source_risk: str,
    domain: str,
) -> dict[str, Any]:
    return {
        "query_overlap": lexical_overlap(query, f"{title} {snippet}"),
        "snippet_overlap": lexical_overlap(restored, f"{title} {snippet}"),
        "question_bank_term_hit": has_negative_terms(f"{title} {snippet} {domain}"),
        "domain_penalty": source_risk in {"question_bank_like", "exam_training_like"},
        "positive_domain_hint": any(hint in domain.lower() for hint in POSITIVE_SOURCE_HINTS),
    }


def candidate_score(*, alignment: dict[str, Any], source_risk: str, domain: str) -> float:
    score = 0.15 + float(alignment.get("query_overlap") or 0) * 0.35 + float(alignment.get("snippet_overlap") or 0) * 0.35
    if alignment.get("positive_domain_hint"):
        score += 0.15
    if source_risk in {"question_bank_like", "exam_training_like"}:
        score -= 0.45
    if source_risk == "unknown":
        score -= 0.05
    return max(0.0, min(1.0, score))


def candidate_status(*, source_risk: str, score: float) -> str:
    if source_risk in {"question_bank_like", "exam_training_like"}:
        return "question_bank_like"
    if score >= 0.55:
        return "candidate"
    if score >= 0.25:
        return "weak_candidate"
    return "blocked"


def build_source_candidate_summary(
    *,
    selected: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    provider_status: str,
) -> dict[str, Any]:
    status_counts = Counter(item.get("candidate_status") or "missing" for item in candidates)
    risk_counts = Counter(item.get("source_risk") or "missing" for item in candidates)
    by_sample: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_sample[str(candidate.get("sample_id") or "")].append(candidate)
    samples_with_candidate = sorted(
        sample_id
        for sample_id, rows in by_sample.items()
        if any(row.get("candidate_status") in {"candidate", "weak_candidate"} for row in rows)
    )
    selected_ids = [str(row.get("sample_id") or "") for row in selected]
    samples_blocked = [
        sample_id
        for sample_id in selected_ids
        if sample_id not in samples_with_candidate
    ]
    blockers = []
    if provider_status != "ok":
        blockers.append(provider_status)
    if not candidates:
        blockers.append("no source candidates collected")
    if samples_blocked:
        blockers.append("some samples have no non-question-bank candidate")
    return {
        "summary_version": "v1",
        "sample_count": len(selected),
        "query_count": sum(len(row.get("search_queries") or []) for row in selected),
        "candidate_count": len(candidates),
        "candidate_status_counts": dict(status_counts),
        "source_risk_counts": dict(risk_counts),
        "samples_with_candidate": samples_with_candidate,
        "samples_blocked": samples_blocked,
        "ready_for_human_source_review": bool(candidates and samples_with_candidate),
        "ready_for_material_card_draft": False,
        "main_blockers": blockers,
    }


def render_source_candidate_alignment_report(
    *,
    manifest: dict[str, Any],
    selected: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Source Candidate Alignment Report",
        "",
        "> Candidate sources are unverified. This report does not confirm original sources and does not write material cards or material libraries.",
        "",
        "## Run",
        "",
        f"- provider: `{manifest.get('provider')}`",
        f"- provider_status: `{manifest.get('provider_status')}`",
        f"- run_search: `{manifest.get('run_search')}`",
        f"- source_queries_path: `{manifest.get('source_queries_path')}`",
        f"- selected_sample_count: `{len(selected)}`",
        f"- query_count: `{manifest.get('query_count')}`",
        f"- candidate_count: `{summary.get('candidate_count')}`",
        f"- ready_for_human_source_review: `{summary.get('ready_for_human_source_review')}`",
        f"- ready_for_material_card_draft: `{summary.get('ready_for_material_card_draft')}`",
        "",
        "## Selected Samples",
        "",
    ]
    lines.extend([f"- `{sample_id}`" for sample_id in manifest.get("selected_sample_ids") or []] or ["- None"])
    lines.extend(["", "## Query List", ""])
    for sample in selected:
        lines.append(f"### `{sample.get('sample_id')}`")
        for query in sample.get("search_queries") or []:
            lines.append(f"- [{query.get('query_type')}] {query.get('query')} ({query.get('confidence')})")
        lines.append("")
    lines.extend(["## Candidate Status Distribution", ""])
    lines.extend(counter_lines(summary.get("candidate_status_counts") or {}))
    lines.extend(["", "## Source Risk Distribution", ""])
    lines.extend(counter_lines(summary.get("source_risk_counts") or {}))
    lines.extend(["", "## Top Candidates By Sample", ""])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[str(candidate.get("sample_id") or "")].append(candidate)
    for sample in selected:
        sample_id = str(sample.get("sample_id") or "")
        lines.append(f"### `{sample_id}`")
        rows = sorted(grouped.get(sample_id, []), key=lambda row: float(row.get("candidate_score") or 0), reverse=True)[:5]
        if not rows:
            lines.append("- None")
            lines.append("")
            continue
        for row in rows:
            lines.append(
                "- `{status}` score=`{score}` risk=`{risk}` verified=`False`: [{title}]({url})".format(
                    status=row.get("candidate_status"),
                    score=row.get("candidate_score"),
                    risk=row.get("source_risk"),
                    title=row.get("title") or row.get("domain") or row.get("url"),
                    url=row.get("url") or "",
                )
            )
        lines.append("")
    lines.extend(["## Blocked Samples", ""])
    lines.extend([f"- `{sample_id}`" for sample_id in summary.get("samples_blocked") or []] or ["- None"])
    lines.extend(
        [
            "",
            "## Human Review Checklist",
            "",
            "- Open candidate URLs manually before treating them as source evidence.",
            "- Reject question-bank, answer-analysis, and exam-training pages as original sources.",
            "- Check whether the article text actually contains the restored material, not just overlapping keywords.",
            "- Do not create material_card or passage-service entries until a later source review confirms the source.",
            "",
            "## Boundaries",
            "",
            "- Candidates are unverified.",
            "- No source article was confirmed.",
            "- No material library write happened.",
            "- No material_card was generated.",
            "- No card_specs, prompt, validator, generation, runtime, API, UI, or promotion target was changed.",
        ]
    )
    return "\n".join(lines) + "\n"


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def lexical_overlap(left: str, right: str) -> float:
    left_terms = token_set(left)
    right_terms = token_set(right)
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms)


def token_set(text: str) -> set[str]:
    normalized = str(text or "").lower()
    tokens = set(re.findall(r"[\u4e00-\u9fff]{2,8}|[a-z][a-z0-9_-]{3,}", normalized))
    if tokens:
        return tokens
    return {char for char in normalized if "\u4e00" <= char <= "\u9fff"}


def has_negative_terms(text: str) -> bool:
    haystack = str(text or "").lower()
    return any(term.lower() in haystack for term in NEGATIVE_TERMS) or any(pattern in haystack for pattern in DOMAIN_RISK_PATTERNS)


def domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower()


def strip_query_noise(query: str) -> str:
    return re.sub(r"\s+", " ", str(query or "")).strip()


def truncate_text(text: str, max_chars: int) -> str:
    text = str(text or "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()


def counter_lines(counter: dict[str, Any]) -> list[str]:
    if not counter:
        return ["- None"]
    return [f"- `{key}`: {value}" for key, value in sorted(counter.items())]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded source candidate search from source discovery queries.")
    parser.add_argument("--source-discovery-queries", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-samples", type=int, default=DEFAULT_MAX_SAMPLES)
    parser.add_argument("--max-queries-per-sample", type=int, default=DEFAULT_MAX_QUERIES_PER_SAMPLE)
    parser.add_argument("--max-results-per-query", type=int, default=DEFAULT_MAX_RESULTS_PER_QUERY)
    parser.add_argument("--allowed-risk", default="low")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-search", action="store_true")
    parser.add_argument("--search-provider", choices=("mock", "manual", "web"), default="manual")
    parser.add_argument("--search-api-key-env", default="SOURCE_SEARCH_API_KEY")
    parser.add_argument("--search-timeout-seconds", type=int, default=DEFAULT_SEARCH_TIMEOUT_SECONDS)
    args = parser.parse_args()
    if args.dry_run and args.run_search:
        raise SystemExit("Choose either --dry-run or --run-search, not both.")
    artifacts = run_source_candidate_search_from_queries(
        source_discovery_queries_path=args.source_discovery_queries,
        output_dir=args.output_dir,
        max_samples=args.max_samples,
        max_queries_per_sample=args.max_queries_per_sample,
        max_results_per_query=args.max_results_per_query,
        allowed_risk=args.allowed_risk,
        dry_run=bool(args.dry_run or not args.run_search),
        run_search=bool(args.run_search),
        search_provider=args.search_provider,
        search_api_key_env=args.search_api_key_env,
        search_timeout_seconds=args.search_timeout_seconds,
    )
    print(json.dumps(artifacts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
