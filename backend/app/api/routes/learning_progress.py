from fastapi import APIRouter
from pydantic import BaseModel

from app import learning_progress_store

router = APIRouter()


class LearningProgressResponse(BaseModel):
    xp: int


class AddXPRequest(BaseModel):
    delta: int


@router.get("/learning-progress", response_model=LearningProgressResponse)
def get_learning_progress():
    return learning_progress_store.get_or_create_learning_progress()


@router.post("/learning-progress/xp", response_model=LearningProgressResponse)
def add_xp(request: AddXPRequest):
    new_xp = learning_progress_store.add_xp(request.delta)
    return LearningProgressResponse(xp=new_xp)
