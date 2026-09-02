import time

import jwt
import streamlit as st
import streamlit.components.v1 as components

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

_AUTH_COOKIE = "access_token"
_AUTH_COOKIE_MAX_AGE = 12 * 60 * 60  # khop EXPIRE_HOURS trong backend/app/auth.py


def _set_auth_cookie(token: str) -> None:
    # components.html render trong 1 iframe rieng - document.cookie o day ghi
    # vao cookie cua iframe, KHONG phai trang chinh. Phai qua window.parent.
    components.html(
        f"<script>window.parent.document.cookie = '{_AUTH_COOKIE}={token}; path=/; max-age={_AUTH_COOKIE_MAX_AGE}; SameSite=Lax';</script>",
        height=0,
    )


def _clear_auth_cookie() -> None:
    components.html(
        f"<script>window.parent.document.cookie = '{_AUTH_COOKIE}=; path=/; max-age=0';</script>", height=0
    )


def _restore_session_from_cookie() -> None:
    # st.session_state mat het khi refresh trang (gan voi ket noi WebSocket) -
    # doc lai JWT tu cookie (da ghi luc dang nhap) de khoi phuc, khong bat dang nhap lai.
    token = st.context.cookies.get(_AUTH_COOKIE)
    if not token:
        return
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return
    if payload.get("exp", 0) < time.time():
        return
    st.session_state.access_token = token
    st.session_state.username = payload.get("sub")
    st.session_state.user_role = payload.get("role")


if "access_token" not in st.session_state and not st.session_state.get("_skip_cookie_restore"):
    # st.context.cookies phan anh cookie tai luc ket noi WebSocket duoc thiet
    # lap - KHONG tu cap nhat theo tung st.rerun() trong cung 1 phien dang song.
    # Neu vua dang xuat (xoa cookie qua JS + rerun trong CUNG phien), doc lai o
    # day van thay cookie CU (truoc khi xoa) va se khoi phuc nham - can co "_skip_cookie_restore".
    _restore_session_from_cookie()
st.session_state.pop("_skip_cookie_restore", None)

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
                    _set_auth_cookie(token)
                    # Doi 1 chut de trinh duyet kip tai iframe cua components.html
                    # va chay script ghi cookie truoc khi rerun cat ngang.
                    time.sleep(0.3)
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


def _get_cached_sessions() -> list:
    if "_sessions_cache" not in st.session_state:
        st.session_state._sessions_cache = list_remote_sessions()
    return st.session_state._sessions_cache


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
    st.markdown("### 💬 Trò chuyện")
    if st.button("➕ Mới", use_container_width=True):
        delete_remote_session_if_empty(st.session_state.session_id)
        st.session_state.session_id = None
        st.session_state.messages = []
        if "session_id" in st.query_params:
            del st.query_params["session_id"]
        st.rerun()

    with st.container(height=220):
        for past_session in _get_cached_sessions():
            is_current = past_session["session_id"] == st.session_state.session_id
            label = ("🟢 " if is_current else "") + past_session["title"]
            if st.button(
                label, key=f"session_{past_session['session_id']}", use_container_width=True, disabled=is_current
            ):
                restored = load_remote_session(past_session["session_id"])
                if restored is not None:
                    switch_to_session(past_session["session_id"], restored["messages"])
                    st.rerun()
                else:
                    st.error("Không thể tải phiên này.")

    # Ghim khoi XP/dang xuat o day sidebar. position: sticky KHONG dung duoc o
    # day vi Streamlit boc container qua 1 lop div flex "shrink-to-fit" (stLayoutWrapper)
    # khien sticky khong con khoang de bam (da kiem chung truc tiep tren DOM).
    # Thay bang position: fixed + transform tren the stSidebar de tao containing
    # block rieng cho no (fixed se bam theo khung sidebar thay vi ca cua so trinh
    # duyet). PHAI thu nho chieu cao vung cuon stSidebarContent (khong phai chi
    # them padding-bottom) de no khong con de len phan noi dung ben tren khi o
    # dau trang (padding-bottom chi tao khoang trong o CUOI, van bi de khi chua
    # cuon toi day - da kiem chung truc tiep tren DOM).
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] {
            transform: translateZ(0);
        }
        div[data-testid="stSidebarContent"] {
            height: calc(100% - 130px) !important;
        }
        .st-key-sidebar_footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            padding: 0.5rem 10px 1rem;
            background-color: rgb(38, 39, 48);
            z-index: 999;
        }
        /* st.divider() mac dinh margin 32px tren-duoi (64px tong) - qua day
        cho 1 dong ke mong trong khung footer nho gon, gay khoang trong thua
        va lech voi cac dong xung quanh. */
        .st-key-sidebar_footer hr {
            margin: 0.5rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="sidebar_footer"):
        st.divider()
        st.caption(
            f"⭐ **{st.session_state.total_xp} XP**  ·  {st.session_state.username} ({st.session_state.user_role})"
        )
        logout_clicked = st.button("🚪 Đăng xuất", use_container_width=True)

    if logout_clicked:
        _clear_auth_cookie()
        time.sleep(0.3)
        st.session_state.clear()
        st.session_state._skip_cookie_restore = True
        st.rerun()


if st.session_state.app_mode == "quiz":
    render_quiz()
elif st.session_state.app_mode == "scam_of_day":
    render_scam_of_day()
elif st.session_state.app_mode == "detective":
    render_detective()
else:
    render_chat()
