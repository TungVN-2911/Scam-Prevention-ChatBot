from app.orchestrator.intent_patterns import IntentPatterns


def test_detect_hotline_intent():
    intents = IntentPatterns()
    assert intents.detect("Cho tôi xin số hotline báo cáo lừa đảo").name == "hotline_lookup"


def test_detect_victim_help_intent():
    intents = IntentPatterns()
    assert intents.detect("Tôi vừa chuyển tiền cho một người lạ").name == "victim_help"


def test_detect_ignores_diacritics():
    intents = IntentPatterns()
    assert intents.detect("cho toi so hotline bao cao lua dao").name == "hotline_lookup"


def test_detect_fallback_general_question():
    intents = IntentPatterns()
    assert intents.detect("Hôm nay thời tiết thế nào").name == "general_question"
