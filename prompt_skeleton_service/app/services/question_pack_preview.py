from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from html import unescape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


TEXT_EXTENSIONS = {".json", ".jsonl", ".csv", ".txt", ".md", ".markdown"}
SUPPORTED_EXTENSIONS = sorted([*TEXT_EXTENSIONS, ".doc", ".docx", ".pdf", ".xlsx"])
MAX_TEXT_CHARS = 12000


def build_question_pack_preview(files: list[tuple[str, bytes]]) -> dict[str, Any]:
    previews = [preview_question_pack_file(filename, content) for filename, content in files]
    combined = "\n\n".join(item.get("text_excerpt") or "" for item in previews if item.get("text_excerpt")).strip()
    parsed_count = sum(1 for item in previews if item.get("status") in {"parsed", "parsed_with_warnings", "degraded"})
    manual_count = sum(1 for item in previews if item.get("status") in {"manual_required", "unsupported"})
    return {
        "preview_version": "v1",
        "status": "parsed" if parsed_count and not manual_count else "partial" if parsed_count else "manual_required",
        "supported_formats": SUPPORTED_EXTENSIONS,
        "frontend_direct_preview_formats": sorted(TEXT_EXTENSIONS),
        "file_count": len(previews),
        "parsed_file_count": parsed_count,
        "manual_required_file_count": manual_count,
        "files": previews,
        "combined_text_excerpt": combined[:MAX_TEXT_CHARS],
        "limits": [
            "This preview does not create a dataset by itself.",
            "PDF/DOC extraction may be lossy and should be human-reviewed.",
            "Parsed text is evidence for preview, not formal card configuration.",
        ],
    }


def preview_question_pack_file(filename: str, content: bytes) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    base = {
        "file_name": filename,
        "extension": suffix or "unknown",
        "size_bytes": len(content),
        "status": "manual_required",
        "parser": "unknown",
        "text_excerpt": "",
        "structured_preview": None,
        "warnings": [],
        "requires_human_review": True,
    }
    try:
        if suffix == ".json":
            return {**base, **_preview_json(content)}
        if suffix == ".jsonl":
            return {**base, **_preview_jsonl(content)}
        if suffix == ".csv":
            return {**base, **_preview_csv(content)}
        if suffix in {".txt", ".md", ".markdown"}:
            return {**base, **_preview_text(content, parser=suffix.lstrip("."))}
        if suffix == ".docx":
            return {**base, **_preview_docx(content)}
        if suffix == ".xlsx":
            return {**base, **_preview_xlsx(content)}
        if suffix == ".pdf":
            return {**base, **_preview_pdf(content)}
        if suffix == ".doc":
            return {**base, **_preview_legacy_doc(content)}
        return {
            **base,
            "status": "unsupported",
            "warnings": [f"unsupported_extension:{suffix or 'unknown'}"],
        }
    except Exception as exc:  # pragma: no cover - defensive guard for arbitrary user files
        return {
            **base,
            "status": "manual_required",
            "parser": suffix.lstrip(".") or "unknown",
            "warnings": [f"parse_failed:{type(exc).__name__}:{exc}"],
        }


def _preview_json(content: bytes) -> dict[str, Any]:
    text = _decode_text(content)
    payload = json.loads(text)
    samples = payload.get("samples") if isinstance(payload, dict) else payload if isinstance(payload, list) else None
    return {
        "status": "parsed",
        "parser": "json",
        "text_excerpt": text[:MAX_TEXT_CHARS],
        "structured_preview": {
            "json_type": "array" if isinstance(payload, list) else "object",
            "sample_count": len(samples) if isinstance(samples, list) else None,
            "top_level_keys": list(payload.keys())[:30] if isinstance(payload, dict) else None,
        },
        "warnings": [],
        "requires_human_review": True,
    }


def _preview_jsonl(content: bytes) -> dict[str, Any]:
    text = _decode_text(content)
    rows = []
    warnings = []
    for index, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            warnings.append(f"line_{index}_json_error:{exc.msg}")
    return {
        "status": "parsed_with_warnings" if warnings else "parsed",
        "parser": "jsonl",
        "text_excerpt": text[:MAX_TEXT_CHARS],
        "structured_preview": {
            "row_count": len(rows),
            "first_keys": list(rows[0].keys())[:30] if rows and isinstance(rows[0], dict) else None,
        },
        "warnings": warnings,
        "requires_human_review": True,
    }


def _preview_csv(content: bytes) -> dict[str, Any]:
    text = _decode_text(content)
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return {
        "status": "parsed",
        "parser": "csv",
        "text_excerpt": text[:MAX_TEXT_CHARS],
        "structured_preview": {
            "row_count": len(rows),
            "columns": reader.fieldnames or [],
            "first_row": rows[0] if rows else None,
        },
        "warnings": [],
        "requires_human_review": True,
    }


def _preview_text(content: bytes, *, parser: str) -> dict[str, Any]:
    text = _decode_text(content)
    return {
        "status": "parsed",
        "parser": parser,
        "text_excerpt": text[:MAX_TEXT_CHARS],
        "structured_preview": {
            "line_count": len(text.splitlines()),
            "char_count": len(text),
        },
        "warnings": [],
        "requires_human_review": True,
    }


def _preview_docx(content: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        xml = zf.read("word/document.xml")
    paragraphs = _wordprocessing_paragraphs(xml)
    text = "\n".join(paragraphs)
    warnings = [] if text.strip() else ["docx_text_empty"]
    return {
        "status": "parsed" if text.strip() else "manual_required",
        "parser": "docx_xml",
        "text_excerpt": text[:MAX_TEXT_CHARS],
        "structured_preview": {
            "paragraph_count": len(paragraphs),
            "char_count": len(text),
        },
        "warnings": warnings,
        "requires_human_review": True,
    }


def _preview_xlsx(content: bytes) -> dict[str, Any]:
    rows: list[list[str]] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        shared = _xlsx_shared_strings(zf)
        sheet_names = sorted(name for name in zf.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        for sheet_name in sheet_names[:3]:
            rows.extend(_xlsx_sheet_rows(zf.read(sheet_name), shared)[:80])
    text = "\n".join("\t".join(cell for cell in row if cell is not None) for row in rows)
    return {
        "status": "parsed" if text.strip() else "manual_required",
        "parser": "xlsx_xml",
        "text_excerpt": text[:MAX_TEXT_CHARS],
        "structured_preview": {
            "row_count": len(rows),
            "first_row": rows[0] if rows else None,
        },
        "warnings": [] if text.strip() else ["xlsx_text_empty"],
        "requires_human_review": True,
    }


def _preview_pdf(content: bytes) -> dict[str, Any]:
    text = _optional_pdf_extract(content) or _naive_pdf_text_extract(content)
    warnings = ["pdf_extraction_is_best_effort"]
    return {
        "status": "degraded" if text.strip() else "manual_required",
        "parser": "pdf_best_effort",
        "text_excerpt": text[:MAX_TEXT_CHARS],
        "structured_preview": {
            "char_count": len(text),
        },
        "warnings": warnings if text.strip() else [*warnings, "pdf_text_unavailable"],
        "requires_human_review": True,
    }


def _preview_legacy_doc(content: bytes) -> dict[str, Any]:
    text = _extract_printable_binary_strings(content)
    return {
        "status": "degraded" if text.strip() else "manual_required",
        "parser": "doc_binary_best_effort",
        "text_excerpt": text[:MAX_TEXT_CHARS],
        "structured_preview": {
            "char_count": len(text),
        },
        "warnings": ["legacy_doc_binary_extraction_is_best_effort"] if text.strip() else ["legacy_doc_requires_manual_conversion"],
        "requires_human_review": True,
    }


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _wordprocessing_paragraphs(xml: bytes) -> list[str]:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ET.fromstring(xml)
    paragraphs = []
    for para in root.findall(".//w:p", ns):
        text = "".join(node.text or "" for node in para.findall(".//w:t", ns)).replace("\xa0", " ").strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values = []
    for item in root.iter():
        if _local_name(item.tag) == "si":
            text = "".join(node.text or "" for node in item.iter() if _local_name(node.tag) == "t")
            values.append(text)
    return values


def _xlsx_sheet_rows(xml: bytes, shared: list[str]) -> list[list[str]]:
    root = ET.fromstring(xml)
    rows: list[list[str]] = []
    for row in root.iter():
        if _local_name(row.tag) != "row":
            continue
        cells: list[str] = []
        for cell in row:
            if _local_name(cell.tag) != "c":
                continue
            cell_type = cell.attrib.get("t")
            value = ""
            for child in cell:
                if _local_name(child.tag) == "v" and child.text is not None:
                    value = child.text
                    break
                if _local_name(child.tag) == "is":
                    value = "".join(node.text or "" for node in child.iter() if _local_name(node.tag) == "t")
            if cell_type == "s":
                try:
                    value = shared[int(value)]
                except (ValueError, IndexError):
                    pass
            cells.append(value)
        if any(str(cell).strip() for cell in cells):
            rows.append(cells)
    return rows


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _optional_pdf_extract(content: bytes) -> str:
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            continue
    return ""


def _naive_pdf_text_extract(content: bytes) -> str:
    raw = content.decode("latin-1", errors="ignore")
    chunks = re.findall(r"\(([^()]{2,})\)\s*T[jJ]", raw)
    text = "\n".join(unescape(chunk.replace("\\(", "(").replace("\\)", ")")) for chunk in chunks)
    if text.strip():
        return text
    return "\n".join(match.group(0) for match in re.finditer(r"[\u4e00-\u9fffA-Za-z0-9，。；：、！？（）《》\-_\s]{20,}", raw))


def _extract_printable_binary_strings(content: bytes) -> str:
    decoded = content.decode("latin-1", errors="ignore")
    parts = re.findall(r"[A-Za-z0-9\u4e00-\u9fff，。；：、！？（）《》\s]{8,}", decoded)
    cleaned = [re.sub(r"\s+", " ", part).strip() for part in parts]
    return "\n".join(part for part in cleaned if part)
