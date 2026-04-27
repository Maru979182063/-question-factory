from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Protocol

from tools.leaf_pre_distill.llm_safe_digest import digest_hash


DEFAULT_MODEL = "chat"
DEFAULT_API_KEY_ENV = "LEAF_PRE_DISTILL_LLM_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_TOKENS = 700


class ChatClient(Protocol):
    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        timeout_seconds: int,
        temperature: float,
        max_tokens: int,
    ) -> str:
        ...


class OpenAICompatibleChatClient:
    def __init__(self, *, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = base_url or os.getenv("LEAF_PRE_DISTILL_LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        self.api_key = api_key

    def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        timeout_seconds: int,
        temperature: float,
        max_tokens: int,
    ) -> str:
        api_key = self.api_key
        if not api_key:
            raise RuntimeError("missing LLM API key")
        url = _chat_completions_url(self.base_url)
        body = json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 leaf-pre-distill/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw_text = response.read().decode("utf-8")
                payload = _parse_chat_completion_body(raw_text)
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed with HTTP {exc.code}: {body_text}") from exc
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("LLM response did not include choices")
        return str(choices[0].get("message", {}).get("content") or "")


def _parse_chat_completion_body(raw_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    try:
        payload = json.JSONDecoder(strict=False).decode(raw_text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    content = _parse_sse_chat_content(raw_text)
    return {"choices": [{"message": {"content": content}}]}


def _parse_sse_chat_content(raw_text: str) -> str:
    chunks: list[str] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload_text = line[5:].strip()
        if not payload_text or payload_text == "[DONE]":
            continue
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError:
            continue
        for choice in payload.get("choices") or []:
            delta = choice.get("delta") or {}
            if "content" in delta:
                chunks.append(str(delta.get("content") or ""))
            message = choice.get("message") or {}
            if "content" in message:
                chunks.append(str(message.get("content") or ""))
    if not chunks:
        raise RuntimeError("SSE LLM response did not include content chunks")
    return "".join(chunks)


def run_llm_field_probe(
    *,
    digest: dict[str, Any],
    model: str = DEFAULT_MODEL,
    base_url: str | None = None,
    api_key_env: str = DEFAULT_API_KEY_ENV,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    client: ChatClient | None = None,
) -> dict[str, Any]:
    input_hash = digest_hash(digest)
    messages = build_probe_messages(digest)
    try:
        active_client = client or OpenAICompatibleChatClient(
            base_url=base_url,
            api_key=os.getenv(api_key_env) or os.getenv("OPENAI_API_KEY"),
        )
        raw_text = active_client.complete(
            messages=messages,
            model=model,
            timeout_seconds=timeout_seconds,
            temperature=0.2,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        parsed = _parse_json_output(raw_text)
        return normalize_probe_output(parsed, digest=digest, model=model, input_digest_hash=input_hash)
    except Exception as exc:
        return {
            "probe_version": "v1",
            "enabled": True,
            "model": model,
            "input_digest_hash": input_hash,
            "usable": False,
            "leaf_signature": "",
            "confirmed_fields": {},
            "field_risks": [],
            "schema_gap_comments": [],
            "warnings": ["LLM field probe failed; main leaf_pre_distill flow was not interrupted."],
            "rejected_suggestions": [],
            "should_promote": False,
            "error": str(exc),
            "raw_output": {},
        }


def build_disabled_probe(
    *,
    digest: dict[str, Any],
    model: str = DEFAULT_MODEL,
    reason: str = "LLM field probe disabled.",
    dry_run: bool = False,
) -> dict[str, Any]:
    return {
        "probe_version": "v1",
        "enabled": False,
        "dry_run": dry_run,
        "model": model,
        "input_digest_hash": digest_hash(digest),
        "usable": False,
        "leaf_signature": "",
        "confirmed_fields": {},
        "field_risks": [],
        "schema_gap_comments": [],
        "warnings": [reason],
        "rejected_suggestions": [],
        "should_promote": False,
        "raw_output": {},
    }


def build_probe_messages(digest: dict[str, Any]) -> list[dict[str, str]]:
    digest_json = json.dumps(digest, ensure_ascii=False, sort_keys=True)
    output_schema = {
        "usable": "boolean",
        "leaf_signature": "short string",
        "confirmed_fields": "object of existing field_path to existing proposed_value only",
        "field_risks": [{"field_path": "string", "risk": "string"}],
        "schema_gap_comments": [{"field": "string", "comment": "string"}],
        "warnings": ["string"],
        "should_promote": False,
    }
    user_prompt = (
        "TASK:\n"
        "Review the EVIDENCE_DIGEST and CANDIDATE_FIELDS. Summarize the leaf signature. "
        "Confirm or warn about existing candidate fields. Comment on schema gaps. "
        "Do not invent formal fields. Do not decide promotion.\n\n"
        "EVIDENCE_DIGEST:\n"
        f"{digest_json}\n\n"
        "OUTPUT_SCHEMA:\n"
        f"{json.dumps(output_schema, ensure_ascii=False, sort_keys=True)}\n\n"
        "Only analyze EVIDENCE_DIGEST and CANDIDATE_FIELDS. "
        "Do not treat TASK or OUTPUT_SCHEMA as source material. "
        "Do not use raw task wording as evidence. Return JSON only."
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a cautious field-probe assistant for a leaf pre-distillation lab. "
                "You do not create formal protocol. You only review candidate fields from structured evidence. "
                "You must output JSON only."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]


def normalize_probe_output(
    parsed: dict[str, Any],
    *,
    digest: dict[str, Any],
    model: str,
    input_digest_hash: str,
) -> dict[str, Any]:
    warnings = [str(item) for item in (parsed.get("warnings") or []) if str(item or "").strip()]
    if parsed.get("should_promote"):
        warnings.append("Model promotion decision ignored; should_promote is forced to false.")

    allowed_fields = _allowed_fields(digest)
    confirmed_fields, rejected_suggestions = _sanitize_confirmed_fields(parsed.get("confirmed_fields"), allowed_fields)
    if rejected_suggestions:
        warnings.append("Rejected unknown or unsupported confirmed_fields from model output.")

    return {
        "probe_version": "v1",
        "enabled": True,
        "model": model,
        "input_digest_hash": input_digest_hash,
        "usable": bool(parsed.get("usable")),
        "leaf_signature": _clip(parsed.get("leaf_signature") or parsed.get("signature"), 600),
        "confirmed_fields": confirmed_fields,
        "field_risks": _field_risks(parsed.get("field_risks") or parsed.get("risks")),
        "schema_gap_comments": _schema_gap_comments(parsed.get("schema_gap_comments")),
        "warnings": warnings,
        "rejected_suggestions": rejected_suggestions,
        "should_promote": False,
        "raw_output": parsed,
    }


def _sanitize_confirmed_fields(value: Any, allowed_fields: dict[str, str]) -> tuple[dict[str, str], list[dict[str, str]]]:
    confirmed: dict[str, str] = {}
    rejected: list[dict[str, str]] = []
    items: list[tuple[str, str]] = []
    if isinstance(value, dict):
        items = [(str(field_path), str(proposed_value)) for field_path, proposed_value in value.items()]
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                rejected.append({"field_path": "", "proposed_value": str(item), "reason": "not an object"})
                continue
            field_path = str(item.get("field_path") or item.get("field") or "")
            proposed_value = str(item.get("proposed_value") or item.get("value") or "")
            items.append((field_path, proposed_value))

    for field_path, proposed_value in items:
        expected_value = allowed_fields.get(field_path)
        if expected_value is not None and str(expected_value) == str(proposed_value):
            confirmed[field_path] = proposed_value
        else:
            rejected.append(
                {
                    "field_path": field_path,
                    "proposed_value": proposed_value,
                    "reason": "not present in existing candidates or slot projection",
                }
            )
    return confirmed, rejected


def _allowed_fields(digest: dict[str, Any]) -> dict[str, str]:
    allowed: dict[str, str] = {}
    for candidate in digest.get("field_candidates") or []:
        field_path = str(candidate.get("field_path") or "")
        proposed_value = str(candidate.get("proposed_value") or "")
        if field_path and proposed_value:
            allowed[field_path] = proposed_value
    summary = digest.get("slot_projection_summary") or {}
    for group in ("canonical_slot_updates", "overlay_updates"):
        for field_path, proposed_value in (summary.get(group) or {}).items():
            allowed[str(field_path)] = str(proposed_value)
    return allowed


def _parse_json_output(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM output JSON must be an object")
    return parsed


def _field_risks(value: Any) -> list[dict[str, str]]:
    if not value:
        return []
    if isinstance(value, list):
        result: list[dict[str, str]] = []
        for item in value[:12]:
            if isinstance(item, dict):
                result.append(
                    {
                        "field_path": _clip(item.get("field_path") or item.get("field"), 120),
                        "risk": _clip(item.get("risk") or item.get("comment") or item.get("text"), 400),
                    }
                )
            else:
                result.append({"field_path": "", "risk": _clip(item, 400)})
        return result
    return [{"field_path": "", "risk": _clip(value, 400)}]


def _schema_gap_comments(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value[:12]:
        if isinstance(item, dict):
            result.append(
                {
                    "field": _clip(item.get("field"), 120),
                    "comment": _clip(item.get("comment") or item.get("reason"), 400),
                }
            )
    return result


def _chat_completions_url(base_url: str | None) -> str:
    normalized = (base_url or "https://api.openai.com/v1").rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if not normalized.endswith("/v1"):
        normalized = f"{normalized}/v1"
    return f"{normalized}/chat/completions"


def _clip(value: Any, max_chars: int) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 3)] + "..."
