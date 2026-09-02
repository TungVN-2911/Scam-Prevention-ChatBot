import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.config import settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not settings.jwt_secret_key,
    reason="Cần JWT_SECRET_KEY trong .env để tạo token test",
)

client = TestClient(app)


def _headers_for(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(username, 'user')}"}


def test_speech_to_text_requires_auth():
    response = client.post("/api/speech-to-text", files={"audio": ("a.wav", b"gia-lap-audio", "audio/wav")})
    assert response.status_code == 401


def test_speech_to_text_rejects_empty_file():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    response = client.post("/api/speech-to-text", files={"audio": ("a.wav", b"", "audio/wav")}, headers=headers)
    assert response.status_code == 400


def test_speech_to_text_returns_transcribed_text(monkeypatch):
    monkeypatch.setattr("app.api.routes.speech.transcribe", lambda audio_bytes, mime_type: "xin chào")
    headers = _headers_for(f"test-{uuid.uuid4()}")

    response = client.post(
        "/api/speech-to-text", files={"audio": ("a.wav", b"gia-lap-audio", "audio/wav")}, headers=headers
    )

    assert response.status_code == 200
    assert response.json() == {"text": "xin chào"}
