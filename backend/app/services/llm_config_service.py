from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret, encrypt_secret, mask_secret
from app.db.models import User, UserLLMConfig
from app.repositories.llm_config_repository import LLMConfigRepository
from app.schemas.llm_config import UserLLMConfigResponse, UserLLMConfigUpdate


@dataclass
class RuntimeLLMConfig:
    provider_name: str
    base_url: str
    api_key: str
    default_model: str


class LLMConfigService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = LLMConfigRepository(db)

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

        saved = self.repository.save(config)
        return self._build_response(saved)

    def get_runtime_config_for_user(self, user_id: int) -> RuntimeLLMConfig | None:
        config = self.repository.get_by_user_id(user_id)
        if not config or not config.enabled:
            return None

        api_key = decrypt_secret(config.api_key_encrypted)
        base_url = config.base_url.strip()
        if not api_key or not base_url:
            return None

        return RuntimeLLMConfig(
            provider_name=config.provider_name.strip() or "OpenAI Compatible",
            base_url=base_url,
            api_key=api_key,
            default_model=config.default_model.strip(),
        )

    def _build_response(self, config: UserLLMConfig | None) -> UserLLMConfigResponse:
        if config is None:
            return UserLLMConfigResponse(
                provider_name="OpenAI Compatible",
                base_url=settings.openai_base_url,
                default_model=settings.default_model,
                enabled=False,
                has_api_key=False,
                masked_api_key="",
                is_ready=False,
            )

        api_key = decrypt_secret(config.api_key_encrypted) if config.api_key_encrypted else ""
        return UserLLMConfigResponse(
            provider_name=config.provider_name,
            base_url=config.base_url,
            default_model=config.default_model or settings.default_model,
            enabled=config.enabled,
            has_api_key=bool(api_key),
            masked_api_key=mask_secret(api_key),
            is_ready=bool(config.enabled and api_key and config.base_url.strip()),
            updated_at=config.updated_at,
        )
