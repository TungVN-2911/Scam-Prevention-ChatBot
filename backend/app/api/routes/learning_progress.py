from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import learning_progress_store
from app.auth import get_current_user

router = APIRouter()


class LearningProgressResponse(BaseModel):
    xp: int


class AddXPRequest(BaseModel):
    delta: int


class QuizAttemptRequest(BaseModel):
    topic: str
    correct_count: int
    total_questions: int
    xp_earned: int
    answers: dict[str, int] = {}


class QuizAttemptResponse(BaseModel):
    id: int
    topic: str
    correct_count: int
    total_questions: int
    xp_earned: int
    created_at: str
    answers: dict[str, int] = {}


class DetectiveAttemptRequest(BaseModel):
    case_id: str
    correct_count: int
    total_expected: int
    xp_earned: int
    result: dict = {}


class DetectiveAttemptResponse(BaseModel):
    id: int
    case_id: str
    correct_count: int
    total_expected: int
    xp_earned: int
    created_at: str
    result: dict = {}


@router.get("/learning-progress", response_model=LearningProgressResponse)
def get_learning_progress(user: dict = Depends(get_current_user)):
    return learning_progress_store.get_or_create_learning_progress(user["username"])


@router.post("/learning-progress/xp", response_model=LearningProgressResponse)
def add_xp(request: AddXPRequest, user: dict = Depends(get_current_user)):
    new_xp = learning_progress_store.add_xp(request.delta, user["username"])
    return LearningProgressResponse(xp=new_xp)


@router.post("/learning-progress/quiz-attempts", status_code=204)
def record_quiz_attempt(request: QuizAttemptRequest, user: dict = Depends(get_current_user)):
    learning_progress_store.record_quiz_attempt(
        request.topic, request.correct_count, request.total_questions, request.xp_earned,
        request.answers, user_key=user["username"],
    )


@router.get("/learning-progress/quiz-attempts", response_model=list[QuizAttemptResponse])
def list_quiz_attempts(user: dict = Depends(get_current_user)):
    return learning_progress_store.list_quiz_attempts(user["username"])


@router.post("/learning-progress/detective-attempts", status_code=204)
def record_detective_attempt(request: DetectiveAttemptRequest, user: dict = Depends(get_current_user)):
    learning_progress_store.record_detective_attempt(
        request.case_id, request.correct_count, request.total_expected, request.xp_earned,
        request.result, user_key=user["username"],
    )


@router.get("/learning-progress/detective-attempts", response_model=list[DetectiveAttemptResponse])
def list_detective_attempts(user: dict = Depends(get_current_user)):
    return learning_progress_store.list_detective_attempts(user["username"])
