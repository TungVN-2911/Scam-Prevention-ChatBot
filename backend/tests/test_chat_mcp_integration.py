# Dung stub LLM gateway de test wiring JWT->MCP ma khong ton quota Gemini that.
import asyncio

import pytest

from app.config import settings
from app.orchestrator.chat_orchestrator import ChatOrchestrator

pytestmark = pytest.mark.skipif(
    not settings.jwt_secret_key,
    reason="Cần JWT_SECRET_KEY trong .env để tạo token test",
)


class _StubLLMGateway:
    def __init__(self, reply: str = "stub reply"):
        self.reply = reply
        self.received_mcp_session = "CHUA_GOI"

    async def generate(self, prompt, context="", history=None, mcp_session=None, tool_calls=None):
        self.received_mcp_session = mcp_session
        return self.reply


def test_no_token_never_opens_mcp_session():
    stub = _StubLLMGateway()
    orchestrator = ChatOrchestrator(llm_gateway=stub)

    result = asyncio.run(orchestrator.handle_message("Dấu hiệu lừa đảo là gì?", token=None))

    assert stub.received_mcp_session is None
    assert result["reply"] == "stub reply"


def test_unreachable_mcp_server_falls_back_gracefully():
    original_url = settings.mcp_server_url
    settings.mcp_server_url = "http://127.0.0.1:1/mcp"
    try:
        stub = _StubLLMGateway()
        orchestrator = ChatOrchestrator(llm_gateway=stub)

        result = asyncio.run(
            orchestrator.handle_message("Dấu hiệu lừa đảo là gì?", token="token-bat-ky")
        )

        assert stub.received_mcp_session is None
        assert result["reply"] == "stub reply"
    finally:
        settings.mcp_server_url = original_url
