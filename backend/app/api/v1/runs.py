import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import SessionLocal, get_db
from app.repositories.user_repository import UserRepository
from app.schemas.run import FlowRunResponse, RunCreate, RunEventResponse, RunTaskResponse
from app.services.run_service import RunService, WorkerDispatchError, WorkflowDisabledError, WorkflowNotFoundError


router = APIRouter()


@router.post("/projects/{project_uid}/runs", response_model=FlowRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    project_uid: str,
    payload: RunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlowRunResponse:
    try:
        run = RunService(db).create_run(user=current_user, project_uid=project_uid, payload=payload)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WorkflowDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except WorkerDispatchError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return run


@router.get("/runs/{run_uid}", response_model=FlowRunResponse)
def get_run(
    run_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlowRunResponse:
    run = RunService(db).get_run(current_user, run_uid)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/runs/{run_uid}/tasks", response_model=list[RunTaskResponse])
def list_run_tasks(
    run_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RunTaskResponse]:
    return RunService(db).list_tasks(current_user, run_uid)


@router.get("/runs/{run_uid}/events", response_model=list[RunEventResponse])
def list_run_events(
    run_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RunEventResponse]:
    return RunService(db).list_events(current_user, run_uid)


@router.post("/runs/{run_uid}/cancel", response_model=FlowRunResponse)
def cancel_run(
    run_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlowRunResponse:
    run = RunService(db).cancel_run(current_user, run_uid)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.post("/runs/{run_uid}/resume", response_model=FlowRunResponse)
def resume_run(
    run_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FlowRunResponse:
    try:
        result = RunService(db).resume_run(current_user, run_uid)
    except WorkerDispatchError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if result is False:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only cancelled or failed runs can be resumed.",
        )
    return result


@router.get("/runs/{run_uid}/stream")
async def stream_run(
    run_uid: str,
    access_token: str = Query(...),
) -> StreamingResponse:
    async def event_generator() -> AsyncIterator[str]:
        last_event_id = 0
        while True:
            with SessionLocal() as db:
                user_uid = decode_access_token(access_token)
                if not user_uid:
                    payload = {"type": "error", "message": "Unauthorized"}
                    yield "event: error\n"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break

                current_user = UserRepository(db).get_by_uid(user_uid)
                if current_user is None:
                    payload = {"type": "error", "message": "Unauthorized"}
                    yield "event: error\n"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break

                service = RunService(db)
                run = service.get_run(current_user, run_uid)
                if not run:
                    payload = {"type": "error", "message": "Run not found"}
                    yield "event: error\n"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    break

                fresh_events = service.list_events(current_user, run_uid, since_id=last_event_id)
                for item in fresh_events:
                    last_event_id = max(last_event_id, item.id)
                    payload = item.model_dump(mode="json")
                    yield "event: run.event\n"
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                yield "event: run.state\n"
                yield f"data: {json.dumps(run.model_dump(mode='json'), ensure_ascii=False)}\n\n"

                if run.status in {"COMPLETED", "FAILED", "CANCELLED"}:
                    break

            await asyncio.sleep(1.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
