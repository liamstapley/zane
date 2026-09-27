from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.schemas.agent import AgentManifest

router = APIRouter(prefix="/api")


class ResetRequest(BaseModel):
    confirmation: str


@router.get("/capabilities", response_model=list[AgentManifest])
def capabilities(request: Request) -> list[AgentManifest]:
    return list(request.app.state.manifests.values())


@router.post("/demo/reset")
def reset_demo(body: ResetRequest, request: Request) -> dict[str, str]:
    if body.confirmation != "RESET DEMO DATA":
        raise HTTPException(400, "Explicit reset confirmation required")
    try:
        request.app.state.tasks.database.reset_demo()
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return {"status": "reset"}
