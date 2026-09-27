from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.cssg.agent import CSSGRuntime
from app.agents.henhacks.agent import HenHacksRuntime
from app.agents.orchestrator.agent import load_domain_manifests
from app.api.tasks import router as tasks_router
from app.config import Settings, load_settings
from app.db.database import Database
from app.models.provider import ModelProvider
from app.routing.router import Router
from app.services.tasks import TaskService


def create_app(settings: Settings | None = None, provider: ModelProvider | None = None) -> FastAPI:
    settings = settings or load_settings()
    if settings.zane_model_provider not in {"none", "openai"}:
        raise ValueError(f"Unsupported model provider: {settings.zane_model_provider}")
    if provider is None and settings.zane_model_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when ZANE_MODEL_PROVIDER=openai")
        from app.models.openai import OpenAIProvider

        provider = OpenAIProvider(settings.openai_api_key, settings.zane_openai_model)
    database = Database(Path(settings.zane_database_path))
    manifests = load_domain_manifests()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database.initialize()
        app.state.tasks = TaskService(
            database, Router(manifests, provider),
            {"henhacks": HenHacksRuntime(manifests["henhacks"]), "cssg": CSSGRuntime(manifests["cssg"])},
            manifests,
        )
        yield

    app = FastAPI(title="ZANE", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(tasks_router)
    return app


app = create_app()
