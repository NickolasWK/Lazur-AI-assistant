
import asyncio
import json
import logging

from sqlalchemy import select, update

from app.database.session import async_session
from app.models.evaluation import Evaluation
from app.llm.ollama_client import evaluate_code


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_feedback(result: dict) -> str:
    """Формирует Markdown-отчёт по результатам проверки."""

    lines = [
        "# Результаты проверки лабораторной работы",
        "",
        "## Проверка критериев",
        ""
    ]

    for item in result["criteria"]:
        lines.extend([
            f"### {item['criterion']}",
            f"**Статус:** {item['status']}",
            "",
            item["explanation"],
            ""
        ])

    lines.extend([
        "## Общий итог",
        "",
        result["summary"]
    ])

    return "\n".join(lines)


async def process_evaluation(evaluation_id: int):
    """Обрабатывает одну задачу."""

    try:
        # Получаем данные задачи из базы
        async with async_session() as session:
            evaluation = await session.get(
                Evaluation,
                evaluation_id
            )

            if evaluation is None:
                return

            criteria = evaluation.criteria_markdown
            source_code = evaluation.source_code

        # Отправляем код в Ollama
        result = await evaluate_code(
            criteria_markdown=criteria,
            source_code=source_code
        )

        # Проверяем базовую структуру ответа
        if not isinstance(result.get("criteria"), list):
            raise ValueError("Invalid LLM response: criteria must be a list")

        if not isinstance(result.get("summary"), str):
            raise ValueError("Invalid LLM response: summary must be a string")

        feedback = create_feedback(result)

        # Сохраняем результат
        async with async_session() as session:
            evaluation = await session.get(
                Evaluation,
                evaluation_id
            )

            if evaluation is not None:
                evaluation.result_json = json.dumps(
                    result,
                    ensure_ascii=False
                )
                evaluation.feedback_markdown = feedback
                evaluation.status = "completed"

                await session.commit()

        logger.info("Evaluation %s completed", evaluation_id)

    except Exception as error:
        logger.exception(
            "Evaluation %s failed",
            evaluation_id
        )

        async with async_session() as session:
            evaluation = await session.get(
                Evaluation,
                evaluation_id
            )

            if evaluation is not None:
                evaluation.status = "failed"
                evaluation.error_message = str(error)

                await session.commit()


async def get_next_evaluation():
    """Атомарно забирает одну ожидающую задачу."""

    async with async_session() as session:
        result = await session.execute(
            select(Evaluation.id)
            .where(Evaluation.status == "pending")
            .order_by(Evaluation.created_at)
            .limit(1)
        )

        evaluation_id = result.scalar_one_or_none()

        if evaluation_id is None:
            return None

        claim = await session.execute(
            update(Evaluation)
            .where(
                Evaluation.id == evaluation_id,
                Evaluation.status == "pending"
            )
            .values(status="processing")
        )

        await session.commit()

        if claim.rowcount == 1:
            return evaluation_id

        return None


async def run_worker():
    """Постоянно проверяет очередь и обрабатывает задачи."""

    logger.info("Evaluation worker started")

    while True:
        try:
            evaluation_id = await get_next_evaluation()

            if evaluation_id is None:
                await asyncio.sleep(2)
                continue

            logger.info(
                "Processing evaluation %s",
                evaluation_id
            )

            await process_evaluation(evaluation_id)

        except asyncio.CancelledError:
            logger.info("Evaluation worker stopped")
            raise

        except Exception:
            logger.exception("Worker error")
            await asyncio.sleep(2)
