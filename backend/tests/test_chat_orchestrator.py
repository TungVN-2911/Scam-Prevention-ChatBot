from app.orchestrator.chat_orchestrator import ChatOrchestrator


def test_hotline_intent_returns_formatted_hotlines():
    orchestrator = ChatOrchestrator()
    result = orchestrator.handle_message("Cho tôi số hotline báo cáo lừa đảo")
    assert result["intent"] == "hotline_lookup"
    assert "113" in result["reply"]


def test_general_question_falls_back_gracefully_without_api_keys():
    # Không có GEMINI_API_KEY/PINECONE_API_KEY trong môi trường test — orchestrator
    # vẫn phải trả lời (không được raise lỗi), chỉ là câu trả lời báo chưa cấu hình.
    orchestrator = ChatOrchestrator()
    result = orchestrator.handle_message("Lừa đảo deepfake là gì?")
    assert result["intent"] == "general_question"
    assert isinstance(result["reply"], str)
    assert len(result["reply"]) > 0
