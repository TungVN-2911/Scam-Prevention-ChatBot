from google import genai
from google.genai import types

from app.config import settings

_client = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None
# gemini-3.5-transcribe (model rieng cho transcribe) tra ve rong qua generate_content
# thong thuong, kiem chung thuc te bang audio TTS. Dung model chat thuong kem prompt
# huong dan thi hoat dong dung. Dung ban 3.5 (khac voi 3.6-flash cua Chat chinh) de
# tach quota rieng, khong an vao 20 request/ngay cua Chat.
_MODEL = "gemini-3.5-flash"
_PROMPT = (
    "Hãy phiên âm chính xác nội dung bản ghi âm sau bằng tiếng Việt, "
    "không thêm bất kỳ lời giải thích nào khác, chỉ trả về đúng phần chữ được nói:"
)


def transcribe(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    if _client is None:
        raise RuntimeError("Chưa cấu hình GEMINI_API_KEY")
    response = _client.models.generate_content(
        model=_MODEL,
        contents=[_PROMPT, types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)],
    )
    return (response.text or "").strip()
