
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationCreated,
    EvaluationStatus,
    EvaluationResult
)
from app.services.evaluation_service import (
    create_evaluation,
    get_evaluation,
    get_evaluation_result
)


router = APIRouter(
    prefix="/api/evaluations",
    tags=["Evaluations"]
)


@router.post(
    "",
    response_model=EvaluationCreated,
    status_code=status.HTTP_202_ACCEPTED
)
async def create(
    data: EvaluationCreate,
    session: AsyncSession = Depends(get_session)
):
    return await create_evaluation(session, data)


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationStatus
)
async def get_status(
    evaluation_id: int,
    session: AsyncSession = Depends(get_session)
):
    evaluation = await get_evaluation(
        session,
        evaluation_id
    )

    if evaluation is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not found"
        )

    return evaluation


@router.get(
    "/{evaluation_id}/result",
    response_model=EvaluationResult
)
async def get_result(
    evaluation_id: int,
    session: AsyncSession = Depends(get_session)
):
    result = await get_evaluation_result(
        session,
        evaluation_id
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not found"
        )

    return result
