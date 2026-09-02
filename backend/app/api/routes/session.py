from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import session_store
from app.auth import get_current_user

router = APIRouter()


class SessionCreateResponse(BaseModel):
    session_id: str


class ChatMessageIn(BaseModel):
    role: str
    content: str
    sources: list[str] = []


class SessionState(BaseModel):
    messages: list[ChatMessageIn]


class SessionSummary(BaseModel):
    session_id: str
    title: str
    updated_at: str


class StartSessionRequest(BaseModel):
    content: str
    sources: list[str] = []


@router.post("/session", response_model=SessionCreateResponse)
def create_session(user: dict = Depends(get_current_user)):
    session_id = session_store.create_session(user["username"])
    return SessionCreateResponse(session_id=session_id)


@router.post("/session/start", response_model=SessionCreateResponse)
def start_session(request: StartSessionRequest, user: dict = Depends(get_current_user)):
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Không thể tạo phiên với tin nhắn rỗng")
    session_id = session_store.create_session_with_message(
        "user", request.content, request.sources, user["username"]
    )
    return SessionCreateResponse(session_id=session_id)


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(limit: int = 20, user: dict = Depends(get_current_user)):
    return session_store.list_sessions(limit, user["username"])


@router.get("/session/{session_id}", response_model=SessionState)
def get_session(session_id: str, user: dict = Depends(get_current_user)):
    state = session_store.get_session(session_id, user["username"])
    if state is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên này")
    return SessionState(**state)


@router.post("/session/{session_id}/messages", status_code=204)
def add_message(session_id: str, message: ChatMessageIn, user: dict = Depends(get_current_user)):
    if session_store.get_session(session_id, user["username"]) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên này")
    session_store.append_message(session_id, message.role, message.content, message.sources)


@router.delete("/session/{session_id}", status_code=204)
def delete_session_if_empty(session_id: str, user: dict = Depends(get_current_user)):
    session_store.delete_session_if_empty(session_id, user["username"])
