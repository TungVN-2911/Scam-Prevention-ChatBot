import asyncio
import json

from app.orchestrator.chat_orchestrator import ChatOrchestrator


class _StubRetriever:
    # Luon tra ve 1 match "gan giong" de kich hoat nhanh _is_known_scam ma khong can Pinecone that.
    def query(self, text, top_k=5, category=None):
        return [{"text": "Kich ban lua dao mau de test", "source": "test", "score": 0.42}]


class _AmbiguousVerdictLLM:
    # Gia lap Gemini tra ve cau tra loi khong ro rang (khong chua KHOP/CHUA_BIET) cho buoc phan loai.
    def __init__(self):
        self.prompts_seen: list[str] = []

    async def generate(self, prompt, context="", history=None, mcp_session=None, tool_calls=None):
        self.prompts_seen.append(prompt)
        if len(self.prompts_seen) == 1:
            return "khong chac chan lam"  # verdict khong ro rang: khong co KHOP/CHUA_BIET
        return "cau tra loi cuoi cung"


def test_ambiguous_verdict_defaults_to_not_known_and_flags_situation(tmp_path, monkeypatch):
    # Fail-safe: verdict khong ro rang phai duoc coi la "chua biet chac", KHONG phai "da biet".
    pending_path = tmp_path / "pending_reports.json"
    monkeypatch.setattr("app.pending_reports_store._PATH", pending_path)

    llm = _AmbiguousVerdictLLM()
    orchestrator = ChatOrchestrator(llm_gateway=llm, retriever=_StubRetriever())

    # "nguoi nay yeu cau toi chuyen tien" chi khop pattern cua scam_identification,
    # khong trung substring voi pattern cua bat ky intent nao dung truoc no trong intents.yaml.
    message = "người này yêu cầu tôi chuyển tiền"
    result = asyncio.run(orchestrator.handle_message(message))

    assert result["intent"] == "scam_identification"
    # Prompt cuoi (lan generate thu 2) phai chua canh bao "chua tung ghi nhan".
    assert "chua tung ghi nhan" in llm.prompts_seen[1]
    assert pending_path.exists()
    saved = json.loads(pending_path.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["text"] == message


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
