import streamlit as st

from api_client import (
    ApiError,
    delete_remote_session_if_empty,
    list_remote_sessions,
    load_remote_learning_progress,
    load_remote_session,
    login,
    register,
)
from chat_page import render_chat
from detective_page import render_detective
from quiz_page import render_quiz
from scam_of_day_page import render_scam_of_day

# PHAI la lenh Streamlit dau tien trong script (ke ca truoc man hinh login).
st.set_page_config(page_title="Trợ lý phòng, chống lừa đảo trực tuyến", page_icon="🛡️")

if "access_token" not in st.session_state:
    st.title("🔐 Đăng nhập")
    login_tab, register_tab = st.tabs(["Đăng nhập", "Đăng ký"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submitted = st.form_submit_button("Đăng nhập")
        if submitted:
            if not username or not password:
                st.error("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            else:
                try:
                    token, role = login(username, password)
                    st.session_state.access_token = token
                    st.session_state.username = username
                    st.session_state.user_role = role
                    st.rerun()
                except ApiError as e:
                    st.error(f"Đăng nhập thất bại: {e}")

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Tên đăng nhập mới")
            new_password = st.text_input("Mật khẩu mới", type="password")
            register_submitted = st.form_submit_button("Đăng ký")
        if register_submitted:
            if not new_username or not new_password:
                st.error("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            else:
                try:
                    register(new_username, new_password)
                    st.success("Đăng ký thành công. Chuyển sang tab Đăng nhập để tiếp tục.")
                except ApiError as e:
                    st.error(f"Đăng ký thất bại: {e}")

    st.stop()

MODE_LABELS = {
    "chat": "💬 Chat",
    "scam_of_day": "🛡️ Scam of the Day",
    "detective": "🕵️ Scam Detective",
    "quiz": "🎯 Quiz",
}


def switch_to_session(session_id: str, messages: list) -> None:
    if not st.session_state.get("messages"):
        delete_remote_session_if_empty(st.session_state.get("session_id"))

    st.session_state.session_id = session_id
    st.session_state.messages = messages
    st.session_state.app_mode = "chat"
    st.query_params["session_id"] = session_id


if "app_mode" not in st.session_state:
    st.session_state.app_mode = "chat"
if "quiz_stage" not in st.session_state:
    st.session_state.quiz_stage = "select_topic"
if "detective_stage" not in st.session_state:
    st.session_state.detective_stage = "select_case"

# session_id = None cho toi khi user gui tin nhan dau tien (lazy creation).
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
            del st.query_params["session_id"]

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
        delete_remote_session_if_empty(st.session_state.session_id)
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
                st.error("Không thể tải phiên này.")

    st.divider()
    st.metric("⭐ Tổng XP", st.session_state.total_xp)

    st.divider()
    st.caption(f"Đăng nhập: **{st.session_state.username}** ({st.session_state.user_role})")
    if st.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state.clear()
        st.rerun()


if st.session_state.app_mode == "quiz":
    render_quiz()
elif st.session_state.app_mode == "scam_of_day":
    render_scam_of_day()
elif st.session_state.app_mode == "detective":
    render_detective()
else:
    render_chat()
