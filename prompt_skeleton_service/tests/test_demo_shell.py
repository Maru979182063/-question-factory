from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import yaml
from fastapi.testclient import TestClient

from app.core.settings import get_settings
from app.core.dependencies import get_runtime_registry
from app.main import app


class DemoShellSmokeTest(TestCase):
    def setUp(self) -> None:
        self.tempdir = TemporaryDirectory()
        runtime_source = Path(__file__).resolve().parents[1] / "configs" / "question_runtime.yaml"
        runtime_payload = yaml.safe_load(runtime_source.read_text(encoding="utf-8")) or {}
        runtime_payload.setdefault("ui", {})
        runtime_payload["ui"]["distill_access"] = {
            "enabled": True,
            "key": "unit-test-distill-key",
            "cookie_name": "distill_demo_access",
        }
        self.runtime_path = Path(self.tempdir.name) / "question_runtime.yaml"
        self.runtime_path.write_text(yaml.safe_dump(runtime_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

        os.environ["PROMPT_SERVICE_SECURITY_ENABLED"] = "true"
        os.environ["PROMPT_SERVICE_API_TOKEN"] = "demo-token"
        os.environ["PROMPT_RUNTIME_CONFIG_PATH"] = str(self.runtime_path)
        get_settings.cache_clear()
        get_runtime_registry.cache_clear()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        self.tempdir.cleanup()
        os.environ.pop("PROMPT_SERVICE_SECURITY_ENABLED", None)
        os.environ.pop("PROMPT_SERVICE_API_TOKEN", None)
        os.environ.pop("PROMPT_RUNTIME_CONFIG_PATH", None)
        get_settings.cache_clear()
        get_runtime_registry.cache_clear()

    def test_demo_index_is_public_even_when_security_enabled(self) -> None:
        response = self.client.get("/demo")

        self.assertEqual(response.status_code, 200)
        self.assertIn("言语理解v0.6", response.text)
        self.assertIn('id="builderScreen"', response.text)
        self.assertIn('id="loadingScreen"', response.text)
        self.assertIn('id="resultScreen"', response.text)
        self.assertIn('id="businessSubtype"', response.text)
        self.assertIn('id="specialType"', response.text)
        self.assertIn("/demo-static/app_v2.js", response.text)
        self.assertIn("/demo-static/app_v2_zh_patch.js", response.text)

    def test_demo_static_asset_is_public_even_when_security_enabled(self) -> None:
        response = self.client.get("/demo-static/app_v2.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("QUESTION_FOCUS_OPTIONS", response.text)
        self.assertIn("SPECIAL_TYPE_TREE", response.text)
        self.assertIn("renderSubtypeOptions", response.text)
        self.assertIn("buildGeneratePayload", response.text)
        self.assertIn("renderDistractorPatchPanel", response.text)
        self.assertIn("apply-distractor-patch", response.text)

    def test_demo_page_loads_distill_entry_patch_script(self) -> None:
        response = self.client.get("/demo")

        self.assertEqual(response.status_code, 200)
        self.assertIn("/demo-static/app_v2_zh_patch.js", response.text)

        patch_asset = self.client.get("/demo-static/app_v2_zh_patch.js")
        self.assertEqual(patch_asset.status_code, 200)
        self.assertIn("进入蒸馏训练台", patch_asset.text)
        self.assertIn("请输入训练入口密钥", patch_asset.text)
        self.assertIn("/api/v1/distill/access/verify", patch_asset.text)

    def test_distill_demo_redirects_to_main_demo_without_cookie(self) -> None:
        response = self.client.get("/demo/distill", follow_redirects=False)

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/demo")

    def test_verify_distill_access_sets_cookie_and_allows_demo(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "unit-test-distill-key"})

        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.json()["next"], "/demo/distill")
        self.assertIn("distill_demo_access", verify.headers.get("set-cookie", ""))

        page = self.client.get("/demo/distill")
        self.assertEqual(page.status_code, 200)
        self.assertIn("蒸馏训练工作台", page.text)
        self.assertIn("1. 建 Dataset", page.text)

    def test_verify_distill_access_rejects_wrong_key(self) -> None:
        verify = self.client.post("/api/v1/distill/access/verify", json={"key": "wrong-key"})

        self.assertEqual(verify.status_code, 401)
        self.assertIn("密钥不正确", verify.text)
