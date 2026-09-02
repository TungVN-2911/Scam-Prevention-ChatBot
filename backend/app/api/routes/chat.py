from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import get_current_user
from app.orchestrator.chat_orchestrator import ChatOrchestrator

router = APIRouter()
_orchestrator = ChatOrchestrator()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

class ChatResponse(BaseModel):
    reply: str
    intent: str
    sources: list[str] = []

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    result = await _orchestrator.handle_message(request.message, history=request.history, token=user["token"])
    return ChatResponse(**result)