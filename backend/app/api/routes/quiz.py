import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import DATA_DIR

router = APIRouter()

_QUIZ_FILE = DATA_DIR / "quiz_questions.json"
_QUESTIONS: list[dict] = json.loads(_QUIZ_FILE.read_text(encoding="utf-8"))
_TOPICS = sorted({q["topic"] for q in _QUESTIONS})


class QuizQuestion(BaseModel):
    id: str
    topic: str
    question: str
    options: list[str]
    correct_index: int
    explanation: str


@router.get("/quiz/topics", response_model=list[str])
def list_topics():
    return _TOPICS


@router.get("/quiz", response_model=list[QuizQuestion])
def get_quiz(topic: str):
    questions = [q for q in _QUESTIONS if q["topic"] == topic]
    if not questions:
        raise HTTPException(status_code=404, detail="Không tìm thấy chủ đề này")
    return questions
