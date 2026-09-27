from fastapi import APIRouter, HTTPException, Request

from app.schemas.tasks import ClarificationRequest, DecisionRequest, TaskRequest, TaskSnapshot
from app.services.tasks import InvalidDecision, TaskNotFound, TaskService


router = APIRouter(prefix="/api")


def service(request: Request) -> TaskService:
    return request.app.state.tasks


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/tasks", response_model=TaskSnapshot)
def create_task(body: TaskRequest, request: Request) -> TaskSnapshot:
    return service(request).create(body.message)


@router.get("/tasks/{task_id}", response_model=TaskSnapshot)
def get_task(task_id: str, request: Request) -> TaskSnapshot:
    try:
        return service(request).get(task_id)
    except TaskNotFound as error:
        raise HTTPException(404, "Task not found") from error


@router.post("/tasks/{task_id}/clarify", response_model=TaskSnapshot)
def clarify_task(task_id: str, body: ClarificationRequest, request: Request) -> TaskSnapshot:
    try:
        return service(request).clarify(task_id, body.answer)
    except TaskNotFound as error:
        raise HTTPException(404, "Task not found") from error
    except InvalidDecision as error:
        raise HTTPException(409, str(error)) from error


@router.post("/tasks/{task_id}/decision", response_model=TaskSnapshot)
def decide_task(task_id: str, body: DecisionRequest, request: Request) -> TaskSnapshot:
    try:
        return service(request).decide(task_id, body.approved)
    except TaskNotFound as error:
        raise HTTPException(404, "Task not found") from error
    except InvalidDecision as error:
        raise HTTPException(409, str(error)) from error
