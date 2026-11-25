"""Один последовательный воркер для локальной демонстрации."""

import asyncio
import json
import logging

from sqlalchemy import select, update

from app.models.evaluation import Evaluation
from skeleton.mock_llm import create_feedback, evaluate_code

logger = logging.getLogger(__name__)


async def run_worker(session_factory, delay: float):
    while True:
        async with session_factory() as session:
            evaluation = await session.scalar(
                select(Evaluation)
                .where(Evaluation.status == "pending")
                .order_by(Evaluation.id)
                .limit(1)
            )
            if evaluation is not None:
                evaluation.status = "processing"
                await session.commit()
                evaluation_id = evaluation.id
                criteria = evaluation.criteria_markdown
                source = evaluation.source_code

        if evaluation is None:
            await asyncio.sleep(0.2)
            continue

        try:
            await asyncio.sleep(delay)
            result = await evaluate_code(criteria, source)
            values = {
                "status": "completed",
                "result_json": json.dumps(result, ensure_ascii=False),
                "feedback_markdown": create_feedback(result),
                "error_message": None,
            }
        except Exception:
            logger.exception("Ошибка демонстрационной проверки %s", evaluation_id)
            values = {"status": "failed", "error_message": "Не удалось обработать работу."}

        async with session_factory() as session:
            await session.execute(
                update(Evaluation).where(Evaluation.id == evaluation_id).values(**values)
            )
            await session.commit()
