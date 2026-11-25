"""FastAPI + Jinja2 поверх исходных API, схем и моделей LabCheker."""

import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes import router as api_router
from app.database.session import Base, get_session
from app.models.evaluation import Evaluation
from app.schemas.evaluation import EvaluationCreate
from app.services.evaluation_service import create_evaluation, get_evaluation, get_evaluation_result
from skeleton.worker import run_worker

ROOT = Path(__file__).resolve().parent
MAX_CODE = 128 * 1024
DEFAULT_CRITERIA = """# Лабораторная работа: студенты
1. Создать класс Student со свойствами Name и Age.
2. Использовать List<Student> для хранения студентов.
3. Добавить студента в список."""
EXAMPLE_CODE = """using System;
using System.Collections.Generic;

class Student
{
    public string Name { get; set; } = "";
    public int Age { get; set; }
}

class Program
{
    static void Main()
    {
        var students = new List<Student>();
        students.Add(new Student { Name = "Анна", Age = 20 });
        Console.WriteLine(students.Count);
    }
}"""


def create_app(database_url: str | None = None, mock_delay: float = 0.6) -> FastAPI:
    """Отдельная база и жизненный цикл; исходное приложение не запускается."""
    if database_url is None:
        data_dir = ROOT / "data"
        data_dir.mkdir(exist_ok=True)
        database_url = f"sqlite+aiosqlite:///{(data_dir / 'demo.db').as_posix()}"
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    templates = Jinja2Templates(directory=str(ROOT / "templates"))

    async def demo_session():
        async with sessions() as session:
            yield session

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        # При остановке во время обработки работа продолжится после перезапуска.
        async with sessions() as session:
            await session.execute(
                update(Evaluation)
                .where(Evaluation.status == "processing")
                .values(status="pending")
            )
            await session.commit()
        task = asyncio.create_task(run_worker(sessions, mock_delay))
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await engine.dispose()

    application = FastAPI(title="Lazur", lifespan=lifespan)
    application.dependency_overrides[get_session] = demo_session
    application.include_router(api_router)
    application.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

    def form_page(request, code, error=None):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"code": code, "error": error},
            status_code=422 if error else 200,
        )

    @application.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return form_page(request, EXAMPLE_CODE)

    @application.post("/submit", response_class=HTMLResponse)
    async def submit(
        request: Request,
        session=Depends(get_session),
        source_code: Annotated[str, Form()] = "",
        source_file: Annotated[UploadFile | None, File()] = None,
    ):
        error = None
        if source_file is not None and source_file.filename:
            try:
                if Path(source_file.filename).suffix.lower() not in {".cs", ".txt"}:
                    error = "Выберите файл .cs или .txt."
                else:
                    content = await source_file.read(MAX_CODE + 1)
                    if len(content) > MAX_CODE:
                        error = "Размер файла не должен превышать 128 КБ."
                    else:
                        source_code = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                error = "Сохраните файл в кодировке UTF-8 и повторите отправку."
            finally:
                await source_file.close()
        if error is None:
            if not source_code.strip():
                error = "Добавьте код работы или выберите файл."
            elif len(source_code) > MAX_CODE:
                error = "Допустимо до 131 072 символов кода."
        if error:
            return form_page(request, source_code, error)
        evaluation = await create_evaluation(
            session,
            EvaluationCreate(criteria_markdown=DEFAULT_CRITERIA, source_code=source_code),
        )
        return RedirectResponse(f"/evaluations/{evaluation.id}", status_code=303)

    @application.get("/evaluations/{evaluation_id}", response_class=HTMLResponse)
    async def result_page(request: Request, evaluation_id: int, session=Depends(get_session)):
        evaluation = await get_evaluation(session, evaluation_id)
        if evaluation is None:
            raise HTTPException(status_code=404, detail="Работа не найдена")
        result = await get_evaluation_result(session, evaluation_id)
        return templates.TemplateResponse(
            request=request,
            name="result.html",
            context={"evaluation": evaluation, "result": result},
        )

    @application.get("/api/health")
    async def health():
        return {"status": "ok", "mode": "mock"}

    return application


app = create_app()
