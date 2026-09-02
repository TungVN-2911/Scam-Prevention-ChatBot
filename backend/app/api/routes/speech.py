from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.auth import get_current_user
from app.speech.transcriber import transcribe

router = APIRouter()


@router.post("/speech-to-text")
async def speech_to_text(audio: UploadFile, user: dict = Depends(get_current_user)):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="File âm thanh trống")
    text = transcribe(audio_bytes, mime_type=audio.content_type or "audio/wav")
    return {"text": text}
