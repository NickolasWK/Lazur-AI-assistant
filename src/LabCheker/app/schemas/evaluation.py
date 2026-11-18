
from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationCreate(BaseModel):
    criteria_markdown: str = Field(min_length=1)
    source_code: str = Field(min_length=1)


class EvaluationCreated(BaseModel):
    id: int
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class EvaluationStatus(BaseModel):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class EvaluationResult(BaseModel):
    id: int
    status: str
    result_json: dict | None = None
    feedback_markdown: str | None = None
    error_message: str | None = None
