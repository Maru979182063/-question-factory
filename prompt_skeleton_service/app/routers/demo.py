from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.core.dependencies import get_runtime_registry
from app.services.runtime_registry import RuntimeConfigRegistry

DEMO_INDEX = Path(__file__).resolve().parent.parent / "demo_static" / "index.html"
FORCED_USER_MATERIAL_DEMO_INDEX = Path(__file__).resolve().parent.parent / "demo_static" / "user_material_demo.html"
DISTILL_DEMO_INDEX = Path(__file__).resolve().parent.parent / "demo_static" / "distill_demo.html"
DEMO_ASSET_VERSION = "20260420a"

router = APIRouter(tags=["demo"])


class DistillAccessVerifyRequest(BaseModel):
    key: str


def _response_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }


def _distill_access_config(runtime_registry: RuntimeConfigRegistry):
    return runtime_registry.get().ui.distill_access


def _distill_access_cookie_value(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _has_distill_demo_access(request: Request, runtime_registry: RuntimeConfigRegistry) -> bool:
    config = _distill_access_config(runtime_registry)
    if not config.enabled:
        return True
    expected_key = str(config.key or "").strip()
    if not expected_key:
        return False
    provided = request.cookies.get(config.cookie_name)
    return bool(provided) and provided == _distill_access_cookie_value(expected_key)


@router.get("/demo", include_in_schema=False)
def demo_shell() -> HTMLResponse:
    html = DEMO_INDEX.read_text(encoding="utf-8")
    html = html.replace("/demo-static/styles.css?v=20260408a", f"/demo-static/styles.css?v={DEMO_ASSET_VERSION}")
    html = html.replace("/demo-static/app_v2.js?v=20260408a", f"/demo-static/app_v2.js?v={DEMO_ASSET_VERSION}")
    if f"/demo-static/app_v2_zh_patch.js?v={DEMO_ASSET_VERSION}" not in html:
        html = html.replace(
            "</body>",
            f'    <script src="/demo-static/app_v2_zh_patch.js?v={DEMO_ASSET_VERSION}"></script>\n  </body>',
        )
    return HTMLResponse(content=html, headers=_response_headers())


@router.get("/demo/user-material", include_in_schema=False)
def forced_user_material_demo_shell() -> HTMLResponse:
    html = FORCED_USER_MATERIAL_DEMO_INDEX.read_text(encoding="utf-8")
    html = html.replace("/demo-static/styles.css?v=20260408a", f"/demo-static/styles.css?v={DEMO_ASSET_VERSION}")
    html = html.replace("/demo-static/user_material_demo.js?v=20260408a", f"/demo-static/user_material_demo.js?v={DEMO_ASSET_VERSION}")
    return HTMLResponse(content=html, headers=_response_headers())


@router.get("/demo/distill", include_in_schema=False, response_model=None)
def distill_demo_shell(
    request: Request,
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
):
    if not _has_distill_demo_access(request, runtime_registry):
        return RedirectResponse(url="/demo", status_code=303)
    html = DISTILL_DEMO_INDEX.read_text(encoding="utf-8")
    html = html.replace("/demo-static/styles.css?v=20260408a", f"/demo-static/styles.css?v={DEMO_ASSET_VERSION}")
    html = html.replace("/demo-static/distill_demo.js?v=20260408a", f"/demo-static/distill_demo.js?v={DEMO_ASSET_VERSION}")
    return HTMLResponse(content=html, headers=_response_headers())


@router.post("/api/v1/distill/access/verify")
def verify_distill_access(
    payload: DistillAccessVerifyRequest,
    runtime_registry: RuntimeConfigRegistry = Depends(get_runtime_registry),
) -> JSONResponse:
    config = _distill_access_config(runtime_registry)
    if not config.enabled:
        response = JSONResponse({"ok": True, "next": "/demo/distill"})
        return response

    expected_key = str(config.key or "").strip()
    if not expected_key:
        return JSONResponse(
            status_code=503,
            content={"error": {"message": "蒸馏训练入口尚未配置访问密钥。"}},
            headers=_response_headers(),
        )

    if payload.key != expected_key:
        return JSONResponse(
            status_code=401,
            content={"error": {"message": "密钥不正确，请重新输入。"}},
            headers=_response_headers(),
        )

    response = JSONResponse({"ok": True, "next": "/demo/distill"}, headers=_response_headers())
    response.set_cookie(
        key=config.cookie_name,
        value=_distill_access_cookie_value(expected_key),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=8 * 60 * 60,
    )
    return response
