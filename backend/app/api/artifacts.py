from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.schemas.artifacts import Artifact, ArtifactSummary
from app.services.artifacts import ArtifactNotFound

router = APIRouter(prefix="/api/artifacts")


@router.get("", response_model=list[ArtifactSummary])
def list_artifacts(request: Request) -> list[ArtifactSummary]:
    return request.app.state.tasks.artifacts.list()


@router.get("/{artifact_id}", response_model=Artifact)
def get_artifact(artifact_id: str, request: Request) -> Artifact:
    try:
        return request.app.state.tasks.artifacts.get(artifact_id)
    except ArtifactNotFound as error:
        raise HTTPException(404, "Artifact not found") from error


@router.get("/{artifact_id}/export")
def export_artifact(artifact_id: str, request: Request) -> Response:
    artifact = get_artifact(artifact_id, request)
    return Response(
        content=f"# {artifact.title}\n\n{artifact.content}\n",
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="zane-{artifact.artifact_type.value}-{artifact.id}.md"'},
    )
