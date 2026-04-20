import json
import re
from typing import Any

from bs4 import BeautifulSoup


class ReadabilityLikeExtractor:
    META_TITLE_SELECTORS = [
        'meta[property="og:title"]',
        'meta[property="article:title"]',
        'meta[name="twitter:title"]',
        'meta[name="Title"]',
    ]
    TITLE_SELECTORS = ["h1", ".title", ".article-title", ".content-title"]
    CONTENT_SELECTORS = [
        "article",
        ".article",
        ".article-content",
        ".content",
        ".pages_content",
        ".TRS_Editor",
        ".rm_txt_con",
        ".detail",
        ".post_content",
        "#p-detail",
        "#main-content",
    ]
    DATE_PATTERNS = [
        re.compile(r"\d{4}-\d{2}-\d{2}"),
        re.compile(r"\d{4}/\d{2}/\d{2}"),
        re.compile(r"\d{4}年\d{1,2}月\d{1,2}日"),
    ]
    GENERIC_TITLE_PATTERNS = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in (
            r"^\s*全部导航\s*$",
            r"^\s*[—\-–|丨]*\s*分享\s*[—\-–|丨]*\s*$",
            r"^\s*评论\s*$",
            r"^\s*分享到?\s*$",
            r"^\s*导航\s*$",
            r"^\s*正文\s*$",
        )
    ]
    NOISE_SELECTORS = [
        "script",
        "style",
        "noscript",
        "header",
        "footer",
        "nav",
        ".share",
        ".share-box",
        ".shareBox",
        ".toolbar",
        ".tool",
        ".crumbs",
        ".breadcrumb",
        ".comment",
        ".comments",
        ".recommend",
        ".related",
        ".editor",
        ".copyright",
    ]
    CLEANUP_NOISE_TOKENS = (
        "责任编辑",
        "编辑：",
        "免责声明",
        "版权所有",
        "推荐阅读",
        "相关阅读",
    )

    LEADING_FRONT_MATTER_PATTERNS = [
        re.compile(pattern)
        for pattern in (
            r"^\s*(责任编辑|责编|编辑|作者|来源)[:：\s].*$",
            r"^\s*[\u25cf\u2022\u00b7]?\s*(新华社|人民日报|光明日报|科技日报|中国青年报).*(记者|通讯员|编辑|记者站).*$",
            r"^\s*.*《[^》]+》.*第\s*\d+\s*版.*$",
            r"^\s*第\s*\d+\s*版\s*$",
            r"^\s*.*(供图|摄|图片来源|图源)\s*$",
        )
    ]
    LEADING_FRONT_MATTER_KEYWORDS = (
        "责任编辑",
        "责编",
        "编辑",
        "作者",
        "来源",
        "通讯员",
        "记者",
        "审核",
        "审校",
        "分享",
        "版",
        "供图",
        "图源",
        "图片来源",
    )

    def extract(self, html: str, url: str, source_config: dict[str, Any]) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup=soup, source_config=source_config)

        published_at = None
        meta_candidates = [
            soup.find("meta", attrs={"property": "article:published_time"}),
            soup.find("meta", attrs={"name": "publishdate"}),
            soup.find("meta", attrs={"name": "PubDate"}),
            soup.find("meta", attrs={"name": "publish-date"}),
        ]
        for meta in meta_candidates:
            if meta and meta.get("content"):
                published_at = meta["content"].strip()
                break
        if not published_at:
            text = soup.get_text("\n", strip=True)
            for pattern in self.DATE_PATTERNS:
                match = pattern.search(text)
                if match:
                    published_at = match.group(0)
                    break

        body_text = ""
        content_selectors = list(source_config.get("content_selectors", [])) + self.CONTENT_SELECTORS
        best_body_text = ""
        for selector in content_selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            candidate_text = self._extract_node_text(node)
            if len(candidate_text) > len(best_body_text):
                best_body_text = candidate_text
        body_text = best_body_text

        embedded = self._extract_embedded_payload(soup, html)
        if embedded:
            embedded_title = self._normalize_title(embedded.get("title") or "")
            if embedded_title and not self._is_generic_title(embedded_title, source_config):
                if not title or len(title.strip()) <= 2:
                    title = embedded_title
            if embedded.get("published_at") and not published_at:
                published_at = embedded["published_at"].strip()
            embedded_body = (embedded.get("raw_text") or "").strip()
            if len(embedded_body) > len(body_text):
                body_text = embedded_body

        if not published_at:
            for selector in source_config.get("date_selectors", []):
                node = soup.select_one(selector)
                if node and node.get_text(strip=True):
                    published_at = node.get_text(" ", strip=True)
                    break

        if not body_text:
            paragraphs = [p.get_text(" ", strip=True) for p in soup.select("p") if p.get_text(strip=True)]
            body_text = "\n\n".join(paragraphs[:80])

        body_text = self._cleanup_text(body_text, title=title)
        return {
            "title": title,
            "published_at": published_at,
            "raw_text": body_text,
            "source_url": url,
        }

    def _extract_embedded_payload(self, soup: BeautifulSoup, raw_html: str) -> dict[str, str]:
        next_payload = self._extract_from_next_data(soup)
        if next_payload and next_payload.get("raw_text"):
            return next_payload
        json_payload = self._extract_from_json_response(raw_html)
        if json_payload and json_payload.get("raw_text"):
            return json_payload
        return {}

    def _extract_from_next_data(self, soup: BeautifulSoup) -> dict[str, str]:
        script = soup.find("script", attrs={"id": "__NEXT_DATA__", "type": "application/json"})
        if script is None:
            return {}
        script_text = script.string or script.get_text(strip=True)
        if not script_text:
            return {}
        try:
            payload = json.loads(script_text)
        except json.JSONDecodeError:
            return {}

        page_data = (((payload.get("props") or {}).get("pageProps") or {}).get("data") or {})
        if not isinstance(page_data, dict):
            return {}

        content_html = ((page_data.get("textInfo") or {}).get("content") or page_data.get("content") or "").strip()
        body_text = self._extract_text_from_html_fragment(content_html)
        if not body_text:
            body_text = str(page_data.get("summary") or "").strip()
        return {
            "title": str(page_data.get("title") or page_data.get("name") or "").strip(),
            "published_at": str(page_data.get("pubTime") or page_data.get("publishTime") or "").strip(),
            "raw_text": body_text,
        }

    def _extract_from_json_response(self, raw_html: str) -> dict[str, str]:
        stripped = raw_html.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            return {}
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return {}

        model = payload.get("model")
        if isinstance(model, list):
            model = model[0] if model else {}
        if not isinstance(model, dict):
            return {}

        content_html = ((model.get("textInfo") or {}).get("content") or model.get("content") or "").strip()
        body_text = self._extract_text_from_html_fragment(content_html)
        if not body_text:
            body_text = str(model.get("summary") or "").strip()
        return {
            "title": str(model.get("title") or model.get("name") or "").strip(),
            "published_at": str(model.get("pubTime") or model.get("publishTime") or "").strip(),
            "raw_text": body_text,
        }

    def _extract_text_from_html_fragment(self, fragment_html: str) -> str:
        if not fragment_html:
            return ""
        fragment_soup = BeautifulSoup(fragment_html, "html.parser")
        container = fragment_soup.select_one("article, .article, .article-content, .content, .TRS_Editor, .detail, #main-content, body")
        if container is None:
            container = fragment_soup
        return self._extract_node_text(container)

    def _extract_title(self, *, soup: BeautifulSoup, source_config: dict[str, Any]) -> str:
        candidates: list[str] = []

        for selector in list(source_config.get("title_selectors", [])) + self.TITLE_SELECTORS:
            node = soup.select_one(selector)
            if node and node.get_text(strip=True):
                candidates.append(node.get_text(" ", strip=True))

        for selector in self.META_TITLE_SELECTORS:
            node = soup.select_one(selector)
            if node and node.get("content"):
                candidates.append(str(node.get("content")).strip())

        if soup.title and soup.title.get_text(strip=True):
            candidates.append(soup.title.get_text(" ", strip=True))

        for raw in candidates:
            title = self._normalize_title(raw)
            if not title or self._is_generic_title(title, source_config):
                continue
            return title
        return ""

    def _extract_node_text(self, node) -> str:
        for selector in self.NOISE_SELECTORS:
            for child in node.select(selector):
                child.decompose()
        paragraphs = [p.get_text(" ", strip=True) for p in node.select("p") if p.get_text(strip=True)]
        if paragraphs:
            return "\n\n".join(paragraphs)
        return node.get_text("\n\n", strip=True)

    def _normalize_title(self, value: str) -> str:
        title = " ".join(str(value or "").split())
        if not title:
            return ""
        title = title.replace("\u3000", " ").strip()
        for separator in ("_", "-", "|", "丨", "｜", "·", "—", "–"):
            if separator not in title:
                continue
            left, right = title.rsplit(separator, 1)
            right = right.strip()
            if right and len(right) <= 12 and any(token in right for token in ("网", "报", "频道", "客户端", "官网")):
                title = left.strip()
        return re.sub(r"\s+", " ", title).strip(" _-|丨｜·—–")

    def _is_generic_title(self, title: str, source_config: dict[str, Any]) -> bool:
        if not title:
            return True
        for pattern in self.GENERIC_TITLE_PATTERNS:
            if pattern.search(title):
                return True
        for raw_pattern in source_config.get("exclude_title_patterns", []) or []:
            try:
                if re.search(raw_pattern, title, flags=re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False

    def _cleanup_text(self, text: str, *, title: str = "") -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        paragraphs = []
        for block in re.split(r"\n\s*\n+", text):
            stripped = block.strip()
            if not stripped:
                continue
            if any(token in stripped for token in self.CLEANUP_NOISE_TOKENS):
                continue
            paragraphs.append(stripped)
        paragraphs = self._strip_leading_front_matter(paragraphs, title=title)
        return "\n\n".join(paragraphs).strip()

    def _strip_leading_front_matter(self, paragraphs: list[str], *, title: str = "") -> list[str]:
        cleaned = list(paragraphs)
        normalized_title = self._normalize_title(title)
        while cleaned:
            paragraph = cleaned[0].strip()
            if not paragraph:
                cleaned.pop(0)
                continue
            if normalized_title and self._normalize_title(paragraph) == normalized_title:
                cleaned.pop(0)
                continue
            if self._is_leading_front_matter_paragraph(paragraph):
                cleaned.pop(0)
                continue
            break
        return cleaned

    def _is_leading_front_matter_paragraph(self, paragraph: str) -> bool:
        normalized = " ".join(str(paragraph or "").split()).strip().strip("-—")
        if not normalized:
            return False
        if any(pattern.match(normalized) for pattern in self.LEADING_FRONT_MATTER_PATTERNS):
            return True
        if len(normalized) <= 56 and any(token in normalized for token in self.LEADING_FRONT_MATTER_KEYWORDS):
            return True
        if len(normalized) <= 88 and any(token in normalized for token in ("图为", "画面中", "照片显示", "图中", "这是")):
            if any(token in normalized for token in ("记者", "摄", "供图", "新华社")):
                return True
        return False
