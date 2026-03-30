from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret, encrypt_secret, mask_secret
from app.db.models import User, UserLLMConfig
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.llm_config_repository import LLMConfigRepository
from app.schemas.llm_config import (
    AgentModelOption,
    AgentRuntimeOverrideUpdate,
    DiscoverModelsRequest,
    DiscoverModelsResponse,
    DiscoveredModelOption,
    UserLLMConfigResponse,
    UserLLMConfigUpdate,
)


@dataclass
class RuntimeAgentLLMConfig:
    override_enabled: bool = False
    provider_name: str = ""
    base_url: str = ""
    api_key: str = ""
    default_model: str = ""


@dataclass
class RuntimeLLMConfig:
    provider_name: str
    base_url: str
    api_key: str
    default_model: str
    agent_model_overrides: dict[str, str] = field(default_factory=dict)
    agent_overrides: dict[str, RuntimeAgentLLMConfig] = field(default_factory=dict)


class LLMConfigService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = LLMConfigRepository(db)
        self.catalog_repository = CatalogRepository(db)

    def get_user_config(self, user: User) -> UserLLMConfigResponse:
        config = self.repository.get_by_user_id(user.id)
        return self._build_response(config)

    def update_user_config(self, user: User, payload: UserLLMConfigUpdate) -> UserLLMConfigResponse:
        config = self.repository.get_by_user_id(user.id)
        if config is None:
            config = UserLLMConfig(
                user_id=user.id,
                provider_name="OpenAI Compatible",
                base_url=settings.openai_base_url,
                api_key_encrypted="",
                default_model=settings.default_model,
                enabled=True,
                agent_model_overrides={},
                agent_runtime_overrides={},
            )

        if payload.provider_name is not None:
            config.provider_name = payload.provider_name.strip() or "OpenAI Compatible"
        if payload.base_url is not None:
            config.base_url = payload.base_url.strip() or settings.openai_base_url
        if payload.default_model is not None:
            config.default_model = payload.default_model.strip()
        if payload.enabled is not None:
            config.enabled = payload.enabled

        if payload.clear_api_key:
            config.api_key_encrypted = ""
        elif payload.api_key is not None:
            cleaned_key = payload.api_key.strip()
            if cleaned_key:
                config.api_key_encrypted = encrypt_secret(cleaned_key)

        if payload.agent_model_overrides is not None:
            config.agent_model_overrides = self._normalize_agent_model_overrides(payload.agent_model_overrides)

        if payload.agent_overrides is not None:
            config.agent_runtime_overrides = self._merge_agent_runtime_overrides(
                config.agent_runtime_overrides or {},
                payload.agent_overrides,
            )
            if config.agent_model_overrides:
                legacy_overrides = self._normalize_agent_model_overrides(config.agent_model_overrides)
                for agent_code in payload.agent_overrides:
                    legacy_overrides.pop(agent_code.strip(), None)
                config.agent_model_overrides = legacy_overrides

        saved = self.repository.save(config)
        return self._build_response(saved)

    def get_runtime_config_for_user(self, user_id: int) -> RuntimeLLMConfig | None:
        config = self.repository.get_by_user_id(user_id)
        if config is None:
            return None

        account_api_key = decrypt_secret(config.api_key_encrypted)
        account_enabled = bool(config.enabled and account_api_key and config.base_url.strip())
        legacy_overrides = self._normalize_agent_model_overrides(config.agent_model_overrides or {})
        runtime_agent_overrides = self._build_runtime_agent_overrides(
            config.agent_runtime_overrides or {},
            legacy_overrides,
        )

        has_ready_agent_override = any(
            override.override_enabled and bool(override.base_url.strip() and override.api_key.strip())
            for override in runtime_agent_overrides.values()
        )

        if not account_enabled and not has_ready_agent_override:
            return None

        return RuntimeLLMConfig(
            provider_name=(config.provider_name.strip() if config.enabled else "") or "OpenAI Compatible",
            base_url=config.base_url.strip() if config.enabled else "",
            api_key=account_api_key if config.enabled else "",
            default_model=config.default_model.strip() if config.enabled else "",
            agent_model_overrides=legacy_overrides,
            agent_overrides=runtime_agent_overrides,
        )

    def discover_models(self, user: User, payload: DiscoverModelsRequest) -> DiscoverModelsResponse:
        config = self.repository.get_by_user_id(user.id)
        stored_agent_override = self._get_stored_agent_override(config, payload.agent_code)

        provider_name = payload.provider_name.strip() if payload.provider_name else ""
        if not provider_name and stored_agent_override:
            provider_name = str(stored_agent_override.get("provider_name", "")).strip()
        if not provider_name and config:
            provider_name = config.provider_name.strip()
        if not provider_name:
            provider_name = "OpenAI Compatible"

        base_url = payload.base_url.strip() if payload.base_url else ""
        if not base_url and stored_agent_override:
            base_url = str(stored_agent_override.get("base_url", "")).strip()
        if not base_url and config:
            base_url = config.base_url.strip()
        if not base_url:
            base_url = settings.openai_base_url

        api_key = payload.api_key.strip() if payload.api_key else ""
        used_saved_api_key = False
        if not api_key and stored_agent_override:
            api_key = decrypt_secret(str(stored_agent_override.get("api_key_encrypted", "")))
            used_saved_api_key = bool(api_key)
        if not api_key and config and config.api_key_encrypted:
            api_key = decrypt_secret(config.api_key_encrypted)
            used_saved_api_key = bool(api_key)
        if not api_key:
            raise ValueError("请先填写 API Key，或者先保存一个可用的密钥。")

        try:
            response = httpx.get(
                f"{base_url.rstrip('/')}/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip() or exc.response.reason_phrase
            raise RuntimeError(f"模型列表读取失败：{exc.response.status_code} {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"模型列表读取失败：{exc}") from exc

        payload_json = response.json()
        rows = payload_json.get("data", []) if isinstance(payload_json, dict) else []
        models = self._normalize_discovered_models(rows)
        if not models:
            raise RuntimeError("服务商接口返回成功，但没有返回可识别的模型列表。")

        return DiscoverModelsResponse(
            provider_name=provider_name,
            base_url=base_url,
            used_saved_api_key=used_saved_api_key,
            models=models,
        )

    def _build_response(self, config: UserLLMConfig | None) -> UserLLMConfigResponse:
        if config is None:
            available_roles = self._build_available_roles(
                legacy_model_overrides={},
                stored_agent_overrides={},
                account_provider_name="OpenAI Compatible",
                account_base_url=settings.openai_base_url,
                account_default_model=settings.default_model,
                account_api_key="",
                account_enabled=False,
            )
            return UserLLMConfigResponse(
                provider_name="OpenAI Compatible",
                base_url=settings.openai_base_url,
                default_model=settings.default_model,
                enabled=False,
                has_api_key=False,
                masked_api_key="",
                agent_model_overrides={},
                available_roles=available_roles,
                is_ready=False,
            )

        account_api_key = decrypt_secret(config.api_key_encrypted) if config.api_key_encrypted else ""
        account_enabled = bool(config.enabled and account_api_key and config.base_url.strip())
        legacy_model_overrides = self._normalize_agent_model_overrides(config.agent_model_overrides or {})
        stored_agent_overrides = self._normalize_stored_agent_runtime_overrides(config.agent_runtime_overrides or {})
        available_roles = self._build_available_roles(
            legacy_model_overrides=legacy_model_overrides,
            stored_agent_overrides=stored_agent_overrides,
            account_provider_name=config.provider_name,
            account_base_url=config.base_url,
            account_default_model=config.default_model or settings.default_model,
            account_api_key=account_api_key,
            account_enabled=account_enabled,
        )
        active_agent_model_overrides = {
            item.agent_code: item.default_model
            for item in available_roles
            if item.override_enabled and item.default_model
        }

        return UserLLMConfigResponse(
            provider_name=config.provider_name,
            base_url=config.base_url,
            default_model=config.default_model or settings.default_model,
            enabled=config.enabled,
            has_api_key=bool(account_api_key),
            masked_api_key=mask_secret(account_api_key),
            agent_model_overrides=active_agent_model_overrides,
            available_roles=available_roles,
            is_ready=bool(account_enabled or any(item.is_ready for item in available_roles if item.override_enabled)),
            updated_at=config.updated_at,
        )

    def _normalize_agent_model_overrides(self, overrides: dict[str, str]) -> dict[str, str]:
        valid_agent_codes = {item.agent_code for item in self.catalog_repository.list_agents()}
        normalized: dict[str, str] = {}
        for agent_code, model_name in overrides.items():
            cleaned_code = agent_code.strip()
            cleaned_model = model_name.strip() if isinstance(model_name, str) else ""
            if cleaned_code not in valid_agent_codes or not cleaned_model:
                continue
            normalized[cleaned_code] = cleaned_model
        return normalized

    def _normalize_stored_agent_runtime_overrides(
        self,
        overrides: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        valid_agent_codes = {item.agent_code for item in self.catalog_repository.list_agents()}
        normalized: dict[str, dict[str, Any]] = {}

        for agent_code, raw_value in overrides.items():
            cleaned_code = agent_code.strip()
            if cleaned_code not in valid_agent_codes or not isinstance(raw_value, dict):
                continue

            normalized_value = {
                "override_enabled": bool(raw_value.get("override_enabled", False)),
                "provider_name": str(raw_value.get("provider_name", "")).strip(),
                "base_url": str(raw_value.get("base_url", "")).strip(),
                "default_model": str(raw_value.get("default_model", "")).strip(),
                "api_key_encrypted": str(raw_value.get("api_key_encrypted", "")).strip(),
            }
            if any(
                [
                    normalized_value["override_enabled"],
                    normalized_value["provider_name"],
                    normalized_value["base_url"],
                    normalized_value["default_model"],
                    normalized_value["api_key_encrypted"],
                ]
            ):
                normalized[cleaned_code] = normalized_value

        return normalized

    def _merge_agent_runtime_overrides(
        self,
        existing: dict[str, Any],
        updates: dict[str, AgentRuntimeOverrideUpdate],
    ) -> dict[str, dict[str, Any]]:
        merged = self._normalize_stored_agent_runtime_overrides(existing)
        valid_agent_codes = {item.agent_code for item in self.catalog_repository.list_agents()}

        for agent_code, payload in updates.items():
            cleaned_code = agent_code.strip()
            if cleaned_code not in valid_agent_codes:
                continue

            current = dict(merged.get(cleaned_code, {}))
            provider_name = (
                payload.provider_name.strip()
                if payload.provider_name is not None
                else str(current.get("provider_name", "")).strip()
            )
            base_url = (
                payload.base_url.strip()
                if payload.base_url is not None
                else str(current.get("base_url", "")).strip()
            )
            default_model = (
                payload.default_model.strip()
                if payload.default_model is not None
                else str(current.get("default_model", "")).strip()
            )
            api_key_encrypted = str(current.get("api_key_encrypted", "")).strip()
            if payload.clear_api_key:
                api_key_encrypted = ""
            elif payload.api_key is not None and payload.api_key.strip():
                api_key_encrypted = encrypt_secret(payload.api_key)

            normalized = {
                "override_enabled": bool(payload.override_enabled),
                "provider_name": provider_name,
                "base_url": base_url,
                "default_model": default_model,
                "api_key_encrypted": api_key_encrypted,
            }
            if any(
                [
                    normalized["override_enabled"],
                    normalized["provider_name"],
                    normalized["base_url"],
                    normalized["default_model"],
                    normalized["api_key_encrypted"],
                ]
            ):
                merged[cleaned_code] = normalized
            else:
                merged.pop(cleaned_code, None)

        return merged

    def _build_runtime_agent_overrides(
        self,
        stored_overrides: dict[str, Any],
        legacy_model_overrides: dict[str, str],
    ) -> dict[str, RuntimeAgentLLMConfig]:
        normalized_stored = self._normalize_stored_agent_runtime_overrides(stored_overrides)
        runtime_overrides: dict[str, RuntimeAgentLLMConfig] = {}
        all_codes = set(legacy_model_overrides) | set(normalized_stored)

        for agent_code in all_codes:
            stored = normalized_stored.get(agent_code, {})
            legacy_model = legacy_model_overrides.get(agent_code, "")
            runtime_overrides[agent_code] = RuntimeAgentLLMConfig(
                override_enabled=bool(stored.get("override_enabled", False) or (legacy_model and not stored)),
                provider_name=str(stored.get("provider_name", "")).strip(),
                base_url=str(stored.get("base_url", "")).strip(),
                api_key=decrypt_secret(str(stored.get("api_key_encrypted", ""))),
                default_model=str(stored.get("default_model", "")).strip() or legacy_model,
            )

        return runtime_overrides

    def _build_available_roles(
        self,
        *,
        legacy_model_overrides: dict[str, str],
        stored_agent_overrides: dict[str, dict[str, Any]],
        account_provider_name: str,
        account_base_url: str,
        account_default_model: str,
        account_api_key: str,
        account_enabled: bool,
    ) -> list[AgentModelOption]:
        options: list[AgentModelOption] = []

        for item in self.catalog_repository.list_agents():
            stored = stored_agent_overrides.get(item.agent_code, {})
            override_api_key = decrypt_secret(str(stored.get("api_key_encrypted", "")))
            default_model = str(stored.get("default_model", "")).strip() or legacy_model_overrides.get(item.agent_code, "")
            override_enabled = bool(stored.get("override_enabled", False) or (legacy_model_overrides.get(item.agent_code, "") and not stored))
            effective_provider_name = str(stored.get("provider_name", "")).strip() or (account_provider_name.strip() if account_enabled else "")
            effective_base_url = str(stored.get("base_url", "")).strip() or (account_base_url.strip() if account_enabled else "")
            effective_api_key = override_api_key or (account_api_key if account_enabled else "")
            effective_model = default_model or (account_default_model.strip() if account_enabled else "") or item.default_model or settings.default_model

            options.append(
                AgentModelOption(
                    agent_code=item.agent_code,
                    display_name=item.display_name,
                    role_default_model=item.default_model or settings.default_model,
                    enabled=item.enabled,
                    override_enabled=override_enabled,
                    provider_name=str(stored.get("provider_name", "")).strip(),
                    base_url=str(stored.get("base_url", "")).strip(),
                    default_model=default_model,
                    has_api_key=bool(override_api_key),
                    masked_api_key=mask_secret(override_api_key),
                    is_ready=bool(override_enabled and effective_base_url and effective_api_key and effective_model),
                )
            )

        return options

    def _normalize_discovered_models(self, rows: list[Any]) -> list[DiscoveredModelOption]:
        normalized: list[DiscoveredModelOption] = []
        seen = set()
        for item in rows:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id", "")).strip()
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            owned_by_raw = item.get("owned_by")
            owned_by = str(owned_by_raw).strip() if isinstance(owned_by_raw, str) and owned_by_raw.strip() else None
            normalized.append(DiscoveredModelOption(model_id=model_id, owned_by=owned_by))

        normalized.sort(key=lambda item: item.model_id.lower())
        return normalized

    def _get_stored_agent_override(self, config: UserLLMConfig | None, agent_code: str | None) -> dict[str, Any] | None:
        if config is None or not agent_code:
            return None
        normalized = self._normalize_stored_agent_runtime_overrides(config.agent_runtime_overrides or {})
        return normalized.get(agent_code.strip())
