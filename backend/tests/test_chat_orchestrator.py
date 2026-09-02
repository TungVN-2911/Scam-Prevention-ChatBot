import asyncio

from app.orchestrator.chat_orchestrator import ChatOrchestrator


def test_hotline_intent_returns_formatted_hotlines():
    orchestrator = ChatOrchestrator()
    result = asyncio.run(orchestrator.handle_message("Cho tôi số hotline báo cáo lừa đảo"))
    assert result["intent"] == "hotline_lookup"
    assert "113" in result["reply"]


def test_general_question_falls_back_gracefully_without_api_keys():
    orchestrator = ChatOrchestrator()
    result = asyncio.run(orchestrator.handle_message("Lừa đảo deepfake là gì?"))
    assert result["intent"] == "general_question"
    assert isinstance(result["reply"], str)
    assert len(result["reply"]) > 0


def test_handle_message_without_token_does_not_attempt_mcp():
    orchestrator = ChatOrchestrator()
    result = asyncio.run(orchestrator.handle_message("Dấu hiệu lừa đảo là gì?", token=None))
    assert isinstance(result["reply"], str)
    assert len(result["reply"]) > 0
