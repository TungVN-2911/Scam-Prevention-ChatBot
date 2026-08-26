from fastapi import APIRouter
from pydantic import BaseModel

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
def chat(request: ChatRequest):
    result = _orchestrator.handle_message(request.message, history=request.history)
    return ChatResponse(**result)