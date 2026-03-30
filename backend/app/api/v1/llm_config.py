from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.llm_config import DiscoverModelsRequest, DiscoverModelsResponse, UserLLMConfigResponse, UserLLMConfigUpdate
from app.services.llm_config_service import LLMConfigService


router = APIRouter(prefix="/llm-config")


@router.get("", response_model=UserLLMConfigResponse)
def get_llm_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserLLMConfigResponse:
    return LLMConfigService(db).get_user_config(current_user)


@router.put("", response_model=UserLLMConfigResponse)
def update_llm_config(
    payload: UserLLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserLLMConfigResponse:
    return LLMConfigService(db).update_user_config(current_user, payload)


@router.post("/discover-models", response_model=DiscoverModelsResponse)
def discover_models(
    payload: DiscoverModelsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscoverModelsResponse:
    service = LLMConfigService(db)
    try:
        return service.discover_models(current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
