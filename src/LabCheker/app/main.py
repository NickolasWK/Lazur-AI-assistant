
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.database.session import init_db
from app.models.evaluation import Evaluation
from app.api.routes import router
from app.workers.evaluation_worker import run_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    worker_task = asyncio.create_task(run_worker())

    yield

    worker_task.cancel()

    with suppress(asyncio.CancelledError):
        await worker_task


app = FastAPI(
    title="LabChecker API",
    description="Automatic laboratory work evaluation",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
