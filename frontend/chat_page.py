"""Man hinh chat chinh: lich su hoi thoai, cau hoi goi y, gui tin nhan."""

import requests
import streamlit as st

from api_client import create_remote_session_with_first_message, post_chat_message, save_remote_message

SUGGESTED_QUESTIONS = [
    "Dấu hiệu nhận biết lừa đảo giả danh Công an là gì?",
    "Tôi vừa chuyển khoản cho người lạ, giờ phải làm gì?",
    "Số hotline báo cáo lừa đảo là gì?",
    "Lừa đảo đầu tư tiền ảo hoạt động như thế nào?",
]


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
                data = post_chat_message(user_text, history_payload)
                reply, sources = data["reply"], data.get("sources", [])
            except requests.RequestException as exc:
                reply, sources = f"Không thể kết nối tới backend. Chi tiết lỗi: {exc}", []
        st.markdown(reply)
        if sources:
            st.caption("📚 Nguồn: " + ", ".join(sources))

    st.session_state.messages.append({"role": "assistant", "content": reply, "sources": sources})
    save_remote_message(st.session_state.session_id, "assistant", reply, sources)


def render_chat() -> None:
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
