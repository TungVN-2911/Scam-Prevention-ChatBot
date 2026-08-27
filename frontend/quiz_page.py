"""Man hinh Quiz: chon chu de, lam bai, xem ket qua + lich su lam bai."""

from datetime import datetime

import requests
import streamlit as st

from api_client import add_remote_xp, load_quiz, load_remote_quiz_attempts, record_remote_quiz_attempt

TOPIC_LABELS = {
    "scams": "🎭 Nhận diện lừa đảo",
    "prevention": "🛡️ Phòng tránh",
    "recovery": "🆘 Khắc phục hậu quả",
    "regulations": "⚖️ Quy định pháp luật",
}


def render_quiz_answer_review(questions: list[dict], answers: dict) -> None:
    """Hien giai thich cho cac cau tra loi sai - dung chung cho man ket qua
    vua nop bai VA man xem lai lich su (du lieu cau hoi la file tinh nen
    tai lai theo topic luon giong het luc lam bai)."""
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
                        st.error(f"Không thể tải câu hỏi. Chi tiết lỗi: {exc}")
                    else:
                        st.session_state.quiz_topic = topic_key
                        st.session_state.quiz_questions = questions
                        st.session_state.quiz_answers = {}
                        st.session_state.quiz_stage = "in_progress"
                        st.rerun()

        st.divider()
        st.markdown("#### 📜 Lịch sử làm bài gần đây")
        attempts = load_remote_quiz_attempts()
        if not attempts:
            st.caption("Chưa có lượt làm bài nào.")
        else:
            quiz_cache: dict[str, list[dict] | None] = {}
            for attempt in attempts:
                topic_label = TOPIC_LABELS.get(attempt["topic"], attempt["topic"])
                try:
                    time_str = datetime.fromisoformat(attempt["created_at"]).strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    time_str = attempt["created_at"]
                summary = (
                    f"{topic_label} — {attempt['correct_count']}/{attempt['total_questions']} "
                    f"(+{attempt['xp_earned']} XP) · {time_str}"
                )
                with st.expander(summary):
                    if attempt["topic"] not in quiz_cache:
                        try:
                            quiz_cache[attempt["topic"]] = load_quiz(attempt["topic"])
                        except requests.RequestException as exc:
                            quiz_cache[attempt["topic"]] = None
                            st.error(f"Không thể tải lại câu hỏi để xem giải thích. Chi tiết lỗi: {exc}")
                    questions = quiz_cache[attempt["topic"]]
                    if questions is not None:
                        render_quiz_answer_review(questions, attempt["answers"])

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
                # Tinh XP theo cung bac thang voi Scam Detective (100/75/50/20 theo %
                # dung), luu XP vao Learning Progress - doc lap voi conversation session.
                correct_count = sum(1 for q in questions if st.session_state.quiz_answers.get(q["id"]) == q["correct_index"])
                percentage = round(correct_count / len(questions) * 100)
                if percentage >= 100:
                    xp = 100
                elif percentage >= 75:
                    xp = 75
                elif percentage >= 50:
                    xp = 50
                else:
                    xp = 20

                new_total_xp = add_remote_xp(xp)
                record_remote_quiz_attempt(
                    st.session_state.quiz_topic, correct_count, len(questions), xp, st.session_state.quiz_answers
                )
                st.session_state.quiz_correct_count = correct_count
                st.session_state.quiz_last_xp = xp
                if new_total_xp is not None:
                    st.session_state.total_xp = new_total_xp
                    st.session_state.quiz_xp_save_failed = False
                else:
                    st.session_state.quiz_xp_save_failed = True

                st.session_state.quiz_stage = "results"
                st.rerun()

    elif st.session_state.quiz_stage == "results":
        questions = st.session_state.quiz_questions
        answers = st.session_state.quiz_answers
        correct_count = st.session_state.quiz_correct_count

        st.subheader(TOPIC_LABELS[st.session_state.quiz_topic])
        col1, col2 = st.columns(2)
        col1.metric("Kết quả", f"{correct_count}/{len(questions)}")
        col2.metric("XP nhận được", f"+{st.session_state.quiz_last_xp} XP")

        if st.session_state.get("quiz_xp_save_failed"):
            st.warning(
                f"⚠️ Không thể lưu {st.session_state.quiz_last_xp} XP vào hệ thống do lỗi kết nối tới backend. "
                "XP hiển thị ở trên CHƯA được ghi nhận vào tổng điểm — vui lòng thử lại sau."
            )

        render_quiz_answer_review(questions, answers)

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
