
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evaluation import Evaluation
from app.schemas.evaluation import EvaluationCreate


async def create_evaluation(
    session: AsyncSession,
    data: EvaluationCreate
) -> Evaluation:
    evaluation = Evaluation(
        criteria_markdown=data.criteria_markdown,
        source_code=data.source_code,
        status="pending"
    )

    session.add(evaluation)
    await session.commit()
    await session.refresh(evaluation)

    return evaluation


async def get_evaluation(
    session: AsyncSession,
    evaluation_id: int
) -> Evaluation | None:
    result = await session.execute(
        select(Evaluation).where(
            Evaluation.id == evaluation_id
        )
    )

    return result.scalar_one_or_none()


async def get_evaluation_result(
    session: AsyncSession,
    evaluation_id: int
) -> dict | None:
    evaluation = await get_evaluation(
        session,
        evaluation_id
    )

    if evaluation is None:
        return None

    result_json = (
        json.loads(evaluation.result_json)
        if evaluation.result_json
        else None
    )

    return {
        "id": evaluation.id,
        "status": evaluation.status,
        "result_json": result_json,
        "feedback_markdown": evaluation.feedback_markdown,
        "error_message": evaluation.error_message
    }
