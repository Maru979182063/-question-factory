from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from app.schemas.runtime import QuestionRuntimeConfig


class RuntimeConfigRegistry:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self._config: QuestionRuntimeConfig | None = None

    def load(self) -> QuestionRuntimeConfig:
        raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        raw = self._apply_environment_overrides(raw)
        self._config = QuestionRuntimeConfig.model_validate(raw)
        return self._config

    def get(self) -> QuestionRuntimeConfig:
        if self._config is None:
            return self.load()
        return self._config

    def _apply_environment_overrides(self, raw: dict[str, Any]) -> dict[str, Any]:
        config = dict(raw)
        ui = dict(config.get("ui") or {})
        distill_access = dict(ui.get("distill_access") or {})
        env_key = (os.getenv("DISTILL_ACCESS_KEY") or "").strip()
        is_public_demo = "public_demo" in self.config_path.stem

        if env_key:
            if is_public_demo and env_key.lower() in {"admin", "change-me", "change-me-distill-key"}:
                raise ValueError("DISTILL_ACCESS_KEY must not use a default development value in public_demo.")
            distill_access["key"] = env_key
        elif is_public_demo:
            distill_access["key"] = None

        if distill_access:
            ui["distill_access"] = distill_access
            config["ui"] = ui
        return config
