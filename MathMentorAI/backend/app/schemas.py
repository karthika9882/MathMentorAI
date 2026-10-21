from typing import Literal
from pydantic import BaseModel, Field

Language = Literal["en", "ta"]

class SolveRequest(BaseModel):
    student_id: str = Field(default="guest", min_length=1, max_length=80)
    grade: int = Field(default=9, ge=9, le=10)
    language: Language = "en"
    equation: str = Field(min_length=3, max_length=120)

class AnswerRequest(BaseModel):
    student_id: str = Field(default="guest", min_length=1, max_length=80)
    grade: int = Field(default=9, ge=9, le=10)
    language: Language = "en"
    topic: str = Field(default="linear_equations", min_length=1, max_length=80)
    question: str = Field(min_length=1, max_length=240)
    expected_answer: str = Field(min_length=1, max_length=100)
    submitted_answer: str = Field(min_length=1, max_length=100)
