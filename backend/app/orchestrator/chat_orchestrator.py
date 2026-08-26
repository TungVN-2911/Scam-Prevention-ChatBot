import json
import logging
from datetime import datetime, timezone
from typing import Optional
from app.config import DATA_DIR
from app.llm_gateway.base import LLMGateway
from app.llm_gateway.gemini_gateway import GeminiGateway
from app.rag_engine.retrieval import PineconeRetriever
from app.orchestrator.intent_patterns import IntentPatterns
from app.scam_connector.mock_connector import MockScamConnector

logger = logging.getLogger("chat_orchestrator")

_INTENT_TO_CATEGORY = {
        "warning_signs": "prevention",
        "prevention_advice": "prevention",
        "transaction_safety": "prevention",
        "victim_help": "recovery",
        "account_security": "recovery",
        "evidence_collection": "recovery",
        "recovery_guidance": "recovery",
        "regulation_question": "regulations",
        "scam_identification": "scams",
        "scam_pattern_search": "scams",
        }  

class ChatOrchestrator:
    def __init__(
        self, 
        intent_pattern: Optional[IntentPatterns] = None,
        llm_gateway: Optional[LLMGateway] = None,
        retriever: Optional[PineconeRetriever] = None
        ):
        self._intents = intent_pattern or IntentPatterns()
        self._llm = llm_gateway or GeminiGateway()
        self._retriever = retriever or PineconeRetriever()
        self._connector = MockScamConnector()  
        
    def handle_message(self, message: str, history: list = None) -> dict:
        intent = self._intents.detect(message)
        
        if intent.name == "hotline_lookup":
            reply = self._format_hotlines()
            sources = ["data/hotlines.json"]
        else:
            reply, sources = self._answer_with_rag(message=message, history = history or [], intent_name=intent.name)
        return {"reply": reply, "intent": intent.name, "sources": sources}            
        
    def _format_hotlines(self) -> str:
        hotlines = self._connector.list_hotlines()
        lines = [f"- {h.name}: {h.contact} ({h.organization})" for h in hotlines]
        return "Các kênh báo cáo/trình báo lừa đảo chính thức:\n" + "\n".join(lines)
    
    # victim_help duoc them theo Huong B: cau mo ta tinh huong tu nhien ("toi nhan duoc
    # tin nhan yeu cau chuyen tien...") rat de roi vao victim_help hon la scam_identification.
    _SCAM_MATCH_INTENTS = ("scam_identification", "scam_pattern_search", "victim_help")

    def _answer_with_rag(self, message: str, history: list, intent_name: str) -> tuple[str, list[str]]:
        category = _INTENT_TO_CATEGORY.get(intent_name)
        try:
            matches = self._retriever.query(message, top_k=5, category=category)
        except Exception:
            logger.exception("Loi khi truy van Pinecone/Ollama")
            matches = []

        context = "\n\n".join(m.get("text", "") for m in matches if m.get("text"))

        prompt = message
        if intent_name in self._SCAM_MATCH_INTENTS:
            # scam_identification/scam_pattern_search da dung category="scams" nen tai su
            # dung luon "matches" cho buoc phan loai. Rieng victim_help dung category=
            # "recovery" cho cau tra loi chinh, nen can truy van THEM 1 lan rieng vao
            # category="scams" chi de phuc vu buoc phan loai nay.
            scam_matches = matches if category == "scams" else self._query_scams(message)

            is_known = self._is_known_scam(message, self._join_texts(scam_matches)) if scam_matches else False
            if not is_known:
                top_score = scam_matches[0].get("score", 0.0) if scam_matches else 0.0
                self._save_unknown_situation(message, top_score)
                prompt = message + (
                    "\n\n(LUU Y CHO TRO LY: tinh huong nguoi dung mo ta KHONG khop voi bat ky hinh thuc "
                    "lua dao nao trong du lieu duoc cung cap. Hay noi ro day co the la 1 hinh thuc/tinh "
                    "huong lua dao MOI ma he thong chua tung ghi nhan, dong thoi van dua ra cac nguyen "
                    "tac an toan chung phu hop.)"
                )

        try:
            reply = self._llm.generate(prompt=prompt, context=context, history=history)
        except Exception:
            logger.exception("Loi khi goi Gemini API")
            reply = (
                "Xin lỗi, hệ thống đang gặp sự cố kết nối tới dịch vụ AI, chưa thể trả lời ngay lúc này. "
                "Nếu đang gặp tình huống khẩn cấp, vui lòng gọi 113 hoặc liên hệ ngân hàng của bạn ngay."
            )

        source = sorted({m["source"] for m in matches if m.get("source")})
        return reply, source

    def _query_scams(self, message: str) -> list[dict]:
        try:
            return self._retriever.query(message, top_k=3, category="scams")
        except Exception:
            logger.exception("Loi khi truy van Pinecone/Ollama (category=scams) de phan loai")
            return []

    @staticmethod
    def _join_texts(matches: list[dict]) -> str:
        return "\n\n".join(m.get("text", "") for m in matches if m.get("text"))

    def _is_known_scam(self, message: str, context: str) -> bool:
        verdict_prompt = (
            "Duoi day la 1 tinh huong nguoi dung nghi ngo va cac hinh thuc lua dao gan nghia nhat tim duoc "
            "trong co so du lieu (co the khong thuc su lien quan). CHI tra loi dung 1 tu duy nhat, khong "
            "giai thich gi them: 'KHOP' neu tinh huong nay thuc su la 1 trong cac hinh thuc lua dao ben "
            "duoi, hoac 'CHUA_BIET' neu khong khop hinh thuc nao.\n\n"
            f"Tinh huong: {message}"
        )
        try:
            verdict_raw = self._llm.generate(prompt=verdict_prompt, context=context).strip().upper()
        except Exception:
            logger.exception("Loi khi goi Gemini API (phan loai) trong chat")
            return True

        if "CHUA_BIET" in verdict_raw:
            return False
        if "KHOP" in verdict_raw:
            return True
        
        logger.warning("Verdict Gemini khong ro rang trong chat: %r", verdict_raw)
        return True

    def _save_unknown_situation(self, text: str, score: float) -> None:
        path = DATA_DIR / "pending_reports.json"
        try:
            reports = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        except Exception:
            logger.exception("Loi khi doc pending_reports.json, bat dau lai tu danh sach rong")
            reports = []

        reports.append({
            "id": f"PENDING-{len(reports) + 1:04d}",
            "text": text,
            "reported_at": datetime.now(timezone.utc).isoformat(),
            "top_score": round(score, 3),
            "status": "pending_review",
        })
        try:
            path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            logger.exception("Loi khi ghi pending_reports.json")