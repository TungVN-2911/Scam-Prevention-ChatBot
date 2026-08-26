import os

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Trợ lý phòng, chống lừa đảo trực tuyến", page_icon="🛡️")


def create_remote_session() -> str | None:
    try:
        response = requests.post(f"{BACKEND_URL}/api/session", timeout=15)
        response.raise_for_status()
        return response.json()["session_id"]
    except requests.RequestException:
        return None


def create_remote_session_with_first_message(content: str, sources: list[str]) -> str | None:
    """Tao session (lazy) dung luc gui tin nhan dau tien - backend gop tao
    session + luu tin nhan vao 1 transaction duy nhat."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/session/start",
            json={"content": content, "sources": sources},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["session_id"]
    except requests.RequestException:
        return None


def load_remote_session(session_id: str) -> dict | None:
    try:
        response = requests.get(f"{BACKEND_URL}/api/session/{session_id}", timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def save_remote_message(session_id: str | None, role: str, content: str, sources: list[str]) -> None:
    if not session_id:
        return
    try:
        requests.post(
            f"{BACKEND_URL}/api/session/{session_id}/messages",
            json={"role": role, "content": content, "sources": sources},
            timeout=15,
        )
    except requests.RequestException:
        pass  # luu lich su la tinh nang phu, khong lam gian doan trai nghiem chat chinh


def load_remote_learning_progress() -> dict | None:
    try:
        response = requests.get(f"{BACKEND_URL}/api/learning-progress", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def add_remote_xp(delta: int) -> int | None:
    """Cong XP vao Learning Progress (doc lap voi conversation session).
    Tra ve tong XP moi neu thanh cong, None neu that bai - goi noi dung
    KHONG duoc tu y coi nhu da luu thanh cong khi nhan None."""
    try:
        response = requests.post(f"{BACKEND_URL}/api/learning-progress/xp", json={"delta": delta}, timeout=15)
        response.raise_for_status()
        return response.json()["xp"]
    except requests.RequestException:
        return None


def list_remote_sessions() -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/api/sessions", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def delete_remote_session_if_empty(session_id: str | None) -> None:
    if not session_id:
        return
    try:
        requests.delete(f"{BACKEND_URL}/api/session/{session_id}", timeout=15)
    except requests.RequestException:
        pass


def switch_to_session(session_id: str, messages: list) -> None:
    """Chuyen sang 1 conversation session khac. KHONG dung toi total_xp -
    Learning Progress doc lap hoan toan voi conversation session."""
    # Neu phien dang roi khoi chua co tin nhan nao, xoa han de khong tich luy
    # phien rac trong DB (backend chi xoa that neu phien do rong).
    if not st.session_state.get("messages"):
        delete_remote_session_if_empty(st.session_state.get("session_id"))

    st.session_state.session_id = session_id
    st.session_state.messages = messages
    st.session_state.app_mode = "chat"
    st.query_params["session_id"] = session_id

TOPIC_LABELS = {
    "scams": "🎭 Nhận diện lừa đảo",
    "prevention": "🛡️ Phòng tránh",
    "recovery": "🆘 Khắc phục hậu quả",
    "regulations": "⚖️ Quy định pháp luật",
}

SUGGESTED_QUESTIONS = [
    "Dấu hiệu nhận biết lừa đảo giả danh Công an là gì?",
    "Tôi vừa chuyển khoản cho người lạ, giờ phải làm gì?",
    "Số hotline báo cáo lừa đảo là gì?",
    "Lừa đảo đầu tư tiền ảo hoạt động như thế nào?",
]

MODE_LABELS = {
    "chat": "💬 Chat",
    "scam_of_day": "🛡️ Scam of the Day",
    "detective": "🕵️ Scam Detective",
    "quiz": "🎯 Quiz",
}

if "app_mode" not in st.session_state:
    st.session_state.app_mode = "chat"
if "quiz_stage" not in st.session_state:
    st.session_state.quiz_stage = "select_topic"
if "detective_stage" not in st.session_state:
    st.session_state.detective_stage = "select_case"

# --- Conversation session (lazy creation) ---------------------------------
# Mo app KHONG tao conversation session trong DB. Chi khoi phuc phien cu neu
# URL co san session_id hop le; neu khong, giu session_id = None cho toi khi
# user thuc su gui tin nhan dau tien (xem send_message()).
if "session_id" not in st.session_state:
    url_session_id = st.query_params.get("session_id")
    restored = load_remote_session(url_session_id) if url_session_id else None
    if restored is not None:
        st.session_state.session_id = url_session_id
        st.session_state.messages = restored["messages"]
    else:
        st.session_state.session_id = None
        st.session_state.messages = []
        if url_session_id:
            # session_id trong URL da khong con hop le (VD phien da bi don).
            del st.query_params["session_id"]

# --- Learning Progress (XP) -------------------------------------------------
# Hoan toan doc lap voi conversation session o tren: luon load/tao ngay khi
# mo app, khong phu thuoc session_id/tin nhan dau tien/New Chat.
if "total_xp" not in st.session_state:
    progress = load_remote_learning_progress()
    st.session_state.total_xp = progress["xp"] if progress else 0

st.markdown(
    '<h1 style="font-size: 38px; white-space: nowrap;">🛡️ Trợ lý phòng, chống lừa đảo trực tuyến</h1>',
    unsafe_allow_html=True
)
st.caption("Hỏi về dấu hiệu lừa đảo, cách xử lý khi bị lừa, hoặc kênh báo cáo chính thức.")

with st.sidebar:
    st.markdown("### Điều hướng")
    mode_keys = list(MODE_LABELS.keys())
    selected_mode = st.radio(
        "Chọn chức năng",
        options=mode_keys,
        format_func=lambda k: MODE_LABELS[k],
        index=mode_keys.index(st.session_state.app_mode),
        label_visibility="collapsed",
    )
    if selected_mode != st.session_state.app_mode:
        st.session_state.app_mode = selected_mode
        if selected_mode == "quiz":
            st.session_state.quiz_stage = "select_topic"
        st.rerun()

    st.divider()
    st.markdown("### 💬 Cuộc trò chuyện")
    if st.button("➕ Cuộc trò chuyện mới", use_container_width=True):
        # Chi reset conversation state cuc bo - KHONG tao session trong DB o
        # day, va KHONG dung toi total_xp (Learning Progress doc lap, giu
        # nguyen). Session chi thuc su duoc tao khi user gui tin nhan dau
        # tien (send_message()).
        delete_remote_session_if_empty(st.session_state.session_id)  # lop bao ve neu phien cu con dang rong
        st.session_state.session_id = None
        st.session_state.messages = []
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
        st.rerun()

    for past_session in list_remote_sessions():
        is_current = past_session["session_id"] == st.session_state.session_id
        label = ("🟢 " if is_current else "") + past_session["title"]
        if st.button(label, key=f"session_{past_session['session_id']}", use_container_width=True, disabled=is_current):
            restored = load_remote_session(past_session["session_id"])
            if restored is not None:
                switch_to_session(past_session["session_id"], restored["messages"])
                st.rerun()
            else:
                st.error(f"Không thể tải phiên này ({BACKEND_URL}).")

    st.divider()
    st.metric("⭐ Tổng XP", st.session_state.total_xp)


def send_message(user_text: str) -> None:
    """Gửi user_text tới backend; hiển thị tin nhắn user ngay lập tức và spinner khi đang chờ trả lời."""
    if not user_text.strip():
        return  # khong tao session/luu tin nhan cho noi dung rong

    history_payload = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": user_text, "sources": []})

    if st.session_state.session_id is None:
        # Lazy creation: day la tin nhan dau tien cua phien nay - tao session
        # va luu tin nhan dau tien trong 1 buoc atomic (xem session_store.
        # create_session_with_message).
        new_session_id = create_remote_session_with_first_message(user_text, [])
        st.session_state.session_id = new_session_id
        if new_session_id:
            st.query_params["session_id"] = new_session_id
    else:
        save_remote_message(st.session_state.session_id, "user", user_text, [])

    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm câu trả lời..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/chat",
                    json={"message": user_text, "history": history_payload},
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                reply, sources = data["reply"], data.get("sources", [])
            except requests.RequestException as exc:
                reply, sources = f"Không thể kết nối tới backend ({BACKEND_URL}). Chi tiết lỗi: {exc}", []
        st.markdown(reply)
        if sources:
            st.caption("📚 Nguồn: " + ", ".join(sources))

    st.session_state.messages.append({"role": "assistant", "content": reply, "sources": sources})
    save_remote_message(st.session_state.session_id, "assistant", reply, sources)


def load_quiz(topic: str) -> list[dict]:
    response = requests.get(f"{BACKEND_URL}/api/quiz", params={"topic": topic}, timeout=30)
    response.raise_for_status()
    return response.json()


def render_quiz() -> None:
    st.header("📝 Kiểm tra kiến thức chống lừa đảo")

    if st.session_state.quiz_stage == "select_topic":
        st.write("Chọn một chủ đề để bắt đầu bài kiểm tra gồm 10 câu hỏi:")
        cols = st.columns(2)
        for i, (topic_key, label) in enumerate(TOPIC_LABELS.items()):
            with cols[i % 2]:
                if st.button(label, key=f"topic_{topic_key}", use_container_width=True):
                    try:
                        questions = load_quiz(topic_key)
                    except requests.RequestException as exc:
                        st.error(f"Không thể tải câu hỏi ({BACKEND_URL}). Chi tiết lỗi: {exc}")
                    else:
                        st.session_state.quiz_topic = topic_key
                        st.session_state.quiz_questions = questions
                        st.session_state.quiz_answers = {}
                        st.session_state.quiz_stage = "in_progress"
                        st.rerun()

    elif st.session_state.quiz_stage == "in_progress":
        questions = st.session_state.quiz_questions
        st.subheader(TOPIC_LABELS[st.session_state.quiz_topic])
        with st.form("quiz_form"):
            for idx, q in enumerate(questions):
                st.markdown(f"**Câu {idx + 1}. {q['question']}**")
                selected = st.radio(
                    "Chọn đáp án",
                    options=list(range(len(q["options"]))),
                    format_func=lambda opt_i, opts=q["options"]: opts[opt_i],
                    key=f"answer_{q['id']}",
                    index=None,
                    label_visibility="collapsed",
                )
                st.session_state.quiz_answers[q["id"]] = selected
                st.divider()
            submitted = st.form_submit_button("✅ Nộp bài")

        if submitted:
            unanswered = [i + 1 for i, q in enumerate(questions) if st.session_state.quiz_answers.get(q["id"]) is None]
            if unanswered:
                st.warning("Bạn chưa trả lời câu: " + ", ".join(map(str, unanswered)))
            else:
                st.session_state.quiz_stage = "results"
                st.rerun()

    elif st.session_state.quiz_stage == "results":
        questions = st.session_state.quiz_questions
        answers = st.session_state.quiz_answers
        correct_count = sum(1 for q in questions if answers.get(q["id"]) == q["correct_index"])

        st.subheader(TOPIC_LABELS[st.session_state.quiz_topic])
        st.metric("Kết quả", f"{correct_count}/{len(questions)}")

        wrong_questions = [(i, q) for i, q in enumerate(questions) if answers.get(q["id"]) != q["correct_index"]]
        if wrong_questions:
            st.markdown("### Giải thích các câu trả lời sai")
            for idx, q in wrong_questions:
                your_answer = answers.get(q["id"])
                st.markdown(f"**Câu {idx + 1}. {q['question']}**")
                st.markdown(f"- Bạn chọn: {q['options'][your_answer]}")
                st.markdown(f"- Đáp án đúng: {q['options'][q['correct_index']]}")
                st.info(q["explanation"])
                st.divider()
        else:
            st.success("Chúc mừng! Bạn đã trả lời đúng tất cả các câu hỏi.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Làm lại chủ đề này", use_container_width=True):
                for q in questions:
                    st.session_state.pop(f"answer_{q['id']}", None)
                st.session_state.quiz_answers = {}
                st.session_state.quiz_stage = "in_progress"
                st.rerun()
        with col2:
            if st.button("📚 Chọn chủ đề khác", use_container_width=True):
                st.session_state.quiz_stage = "select_topic"
                st.rerun()


def load_scam_of_day() -> dict:
    response = requests.get(f"{BACKEND_URL}/api/scam-of-day", timeout=30)
    response.raise_for_status()
    return response.json()


def load_detective_cases() -> list[dict]:
    response = requests.get(f"{BACKEND_URL}/api/detective/cases", timeout=30)
    response.raise_for_status()
    return response.json()


def load_detective_case(case_id: str) -> dict:
    response = requests.get(f"{BACKEND_URL}/api/detective/cases/{case_id}", timeout=30)
    response.raise_for_status()
    return response.json()


def submit_detective_case(case_id: str, selected_signal_ids: list[str]) -> dict:
    response = requests.post(
        f"{BACKEND_URL}/api/detective/cases/{case_id}/submit",
        json={"selected_signal_ids": selected_signal_ids},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def start_detective_case(case_id: str) -> None:
    st.session_state.detective_case = load_detective_case(case_id)
    st.session_state.detective_stage = "case"
    st.session_state.detective_result = None


def render_scam_of_day() -> None:
    st.header("🛡️ Scam of the Day")
    try:
        data = load_scam_of_day()
    except requests.RequestException as exc:
        st.error(f"Không thể tải dữ liệu ({BACKEND_URL}). Chi tiết lỗi: {exc}")
        return

    pattern = data["pattern"]
    with st.container(border=True):
        st.subheader(pattern["name"])
        st.caption(f"Hình thức lừa đảo trong ngày {data['date']}")
        st.markdown(pattern.get("description") or pattern.get("scenario") or "")

        st.markdown("**Dấu hiệu:**")
        for sign in pattern.get("warning_signs", []):
            st.markdown(f"- {sign}")

        st.markdown("**Nên làm:**")
        for action in pattern.get("prevention", []):
            st.markdown(f"- {action}")

        source = pattern.get("source") or {}
        source_label = " — ".join(v for v in [source.get("organization"), source.get("title")] if v)
        if source_label:
            if source.get("url"):
                st.caption(f"📚 Nguồn: [{source_label}]({source['url']})")
            else:
                st.caption(f"📚 Nguồn: {source_label}")

        if st.button("🎯 Thử thách Scam Detective", use_container_width=True):
            try:
                cases = load_detective_cases()
            except requests.RequestException as exc:
                st.error(f"Không thể tải Scam Detective. Chi tiết lỗi: {exc}")
            else:
                matching = next((c for c in cases if c["scam_pattern"] == pattern["slug"]), None)
                st.session_state.app_mode = "detective"
                if matching:
                    start_detective_case(matching["id"])
                else:
                    st.session_state.detective_stage = "select_case"
                    st.session_state.detective_note = (
                        "Chưa có case Scam Detective riêng cho hình thức này, "
                        "hãy chọn 1 case khác bên dưới để luyện tập."
                    )
                st.rerun()


DIFFICULTY_LABELS = {"easy": "🟢 Dễ", "medium": "🟡 Trung bình", "hard": "🔴 Khó"}


def render_detective() -> None:
    st.header("🕵️ Scam Detective")

    if st.session_state.detective_stage == "select_case":
        note = st.session_state.pop("detective_note", None)
        if note:
            st.info(note)
        st.write("Chọn 1 case để luyện tập nhận diện dấu hiệu lừa đảo:")
        try:
            cases = load_detective_cases()
        except requests.RequestException as exc:
            st.error(f"Không thể tải danh sách case ({BACKEND_URL}). Chi tiết lỗi: {exc}")
            return
        for case in cases:
            label = f"{DIFFICULTY_LABELS.get(case['difficulty'], case['difficulty'])} — {case['title']}"
            if st.button(label, key=f"case_{case['id']}", use_container_width=True):
                try:
                    start_detective_case(case["id"])
                except requests.RequestException as exc:
                    st.error(f"Không thể tải case ({BACKEND_URL}). Chi tiết lỗi: {exc}")
                else:
                    st.rerun()

    elif st.session_state.detective_stage == "case":
        case = st.session_state.detective_case
        st.subheader(f"{case['title']} ({DIFFICULTY_LABELS.get(case['difficulty'], case['difficulty'])})")
        with st.container(border=True):
            st.markdown(case["scenario"])
        st.markdown("**Nhiệm vụ:** Hãy chọn những dấu hiệu đáng ngờ mà bạn nhận ra trong tình huống trên.")

        with st.form("detective_form"):
            selected = []
            for signal in case["signals"]:
                if st.checkbox(signal["text"], key=f"signal_{case['id']}_{signal['id']}"):
                    selected.append(signal["id"])
            submitted = st.form_submit_button("✅ Nộp đáp án")

        if submitted:
            try:
                result = submit_detective_case(case["id"], selected)
            except requests.RequestException as exc:
                st.error(f"Không thể chấm điểm ({BACKEND_URL}). Chi tiết lỗi: {exc}")
            else:
                st.session_state.detective_result = result
                st.session_state.detective_selected = selected
                # XP thuoc Learning Progress, doc lap voi conversation session -
                # persist ngay lap tuc, KHONG cho vao session_state truoc khi
                # biet chac da luu thanh cong (database la source of truth).
                new_total_xp = add_remote_xp(result["xp"])
                if new_total_xp is not None:
                    st.session_state.total_xp = new_total_xp
                    st.session_state.detective_xp_save_failed = False
                else:
                    st.session_state.detective_xp_save_failed = True
                st.session_state.detective_stage = "result"
                st.rerun()

    elif st.session_state.detective_stage == "result":
        case = st.session_state.detective_case
        result = st.session_state.detective_result
        selected = set(st.session_state.detective_selected)
        expected = set(result["expected_signals"])

        st.subheader(case["title"])
        col1, col2 = st.columns(2)
        col1.metric("Điểm", f"{result['correct_count']}/{result['total_expected']} ({result['percentage']}%)")
        col2.metric("XP nhận được", f"+{result['xp']} XP")

        if st.session_state.get("detective_xp_save_failed"):
            st.warning(
                f"⚠️ Không thể lưu {result['xp']} XP vào hệ thống do lỗi kết nối tới backend. "
                "XP hiển thị ở trên CHƯA được ghi nhận vào tổng điểm — vui lòng thử lại case này sau."
            )

        st.markdown("### Giải thích")
        for signal in case["signals"]:
            sid = signal["id"]
            was_expected = sid in expected
            was_selected = sid in selected
            if was_expected and was_selected:
                icon = "✅"
            elif was_expected and not was_selected:
                icon = "❌ (bạn đã bỏ lỡ dấu hiệu này)"
            elif not was_expected and was_selected:
                icon = "⚠️ (không phải dấu hiệu lừa đảo)"
            else:
                continue
            st.markdown(f"{icon} **{signal['text']}**")
            st.caption(result["explanations"].get(sid, ""))

        source = case.get("source") or {}
        source_label = " — ".join(v for v in [source.get("organization"), source.get("title")] if v)
        if source_label:
            st.caption(f"📚 Nguồn: {source_label}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➡️ Case tiếp theo", use_container_width=True):
                try:
                    cases = load_detective_cases()
                except requests.RequestException as exc:
                    st.error(f"Không thể tải case tiếp theo. Chi tiết lỗi: {exc}")
                else:
                    ids = [c["id"] for c in cases]
                    current_index = ids.index(case["id"]) if case["id"] in ids else -1
                    next_id = ids[(current_index + 1) % len(ids)]
                    start_detective_case(next_id)
                    st.rerun()
        with col2:
            if st.button("🔁 Chọn case khác", use_container_width=True):
                st.session_state.detective_stage = "select_case"
                st.rerun()


if st.session_state.app_mode == "quiz":
    render_quiz()
elif st.session_state.app_mode == "scam_of_day":
    render_scam_of_day()
elif st.session_state.app_mode == "detective":
    render_detective()
else:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                st.caption("📚 Nguồn: " + ", ".join(message["sources"]))

    pending_question = None
    if not st.session_state.messages:
        st.caption("💡 Câu hỏi gợi ý:")
        cols = st.columns(2)
        for i, question in enumerate(SUGGESTED_QUESTIONS):
            with cols[i % 2]:
                if st.button(question, key=f"suggested_{i}", use_container_width=True):
                    pending_question = question

    typed_question = st.chat_input("Nhập câu hỏi của bạn...")

    if pending_question:
        send_message(pending_question)
    elif typed_question:
        send_message(typed_question)
