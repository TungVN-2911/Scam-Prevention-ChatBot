import os

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


class ApiError(Exception):
    # Message hien thi truc tiep cho nguoi dung - khong bao gio chua URL/status code.
    pass


def _raise_friendly(exc: requests.RequestException, fallback: str):
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            detail = response.json().get("detail")
            if detail:
                raise ApiError(detail) from exc
        except ValueError:
            pass
    raise ApiError(fallback) from exc


# --- Login -------------------------------------------------------------------
def _auth_headers() -> dict:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}

def login(username: str, password: str) -> tuple[str, str]:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/login",
            json={"username": username, "password": password},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_friendly(exc, "Không thể đăng nhập. Vui lòng thử lại sau.")
    data = response.json()
    return data["access_token"], data["role"]


def register(username: str, password: str) -> None:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/register",
            json={"username": username, "password": password},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_friendly(exc, "Không thể đăng ký. Vui lòng thử lại sau.")

# --- Chat -------------------------------------------------------------------

def post_chat_message(message: str, history: list[dict]) -> dict:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat",
            json={"message": message, "history": history},
            headers=_auth_headers(),
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_friendly(exc, "Không thể kết nối tới trợ lý. Vui lòng thử lại sau.")
    return response.json()


# --- Conversation session (lazy creation) ------------------------------------

def create_remote_session_with_first_message(content: str, sources: list[str]) -> str | None:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/session/start",
            json={"content": content, "sources": sources},
            headers=_auth_headers(),
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["session_id"]
    except requests.RequestException:
        return None


def load_remote_session(session_id: str) -> dict | None:
    try:
        response = requests.get(f"{BACKEND_URL}/api/session/{session_id}", headers=_auth_headers(), timeout=15)
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
            headers=_auth_headers(),
            timeout=15,
        )
    except requests.RequestException:
        pass  # tinh nang phu, khong chan luong chat chinh


def list_remote_sessions() -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/api/sessions", headers=_auth_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def delete_remote_session_if_empty(session_id: str | None) -> None:
    if not session_id:
        return
    try:
        requests.delete(f"{BACKEND_URL}/api/session/{session_id}", headers=_auth_headers(), timeout=15)
    except requests.RequestException:
        pass


# --- Learning Progress (XP) --------------------------------------------------

def load_remote_learning_progress() -> dict | None:
    try:
        response = requests.get(f"{BACKEND_URL}/api/learning-progress", headers=_auth_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def add_remote_xp(delta: int) -> int | None:
    # None nghia la luu that bai - goi noi KHONG duoc coi nhu da thanh cong.
    try:
        response = requests.post(f"{BACKEND_URL}/api/learning-progress/xp", headers=_auth_headers(), json={"delta": delta}, timeout=15)
        response.raise_for_status()
        return response.json()["xp"]
    except requests.RequestException:
        return None


# --- Quiz ---------------------------------------------------------------------

def load_quiz(topic: str) -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/api/quiz", params={"topic": topic}, headers=_auth_headers(), timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_friendly(exc, "Không thể tải câu hỏi. Vui lòng thử lại sau.")
    return response.json()


def record_remote_quiz_attempt(
    topic: str, correct_count: int, total_questions: int, xp_earned: int, answers: dict
) -> None:
    try:
        requests.post(
            f"{BACKEND_URL}/api/learning-progress/quiz-attempts",
            json={
                "topic": topic,
                "correct_count": correct_count,
                "total_questions": total_questions,
                "xp_earned": xp_earned,
                "answers": answers,
            },
            headers=_auth_headers(),
            timeout=15,
        )
    except requests.RequestException:
        pass  # tinh nang phu, khong chan viec nop bai


def load_remote_quiz_attempts() -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/api/learning-progress/quiz-attempts", headers=_auth_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


# --- Scam of the Day ----------------------------------------------------------

def load_scam_of_day() -> dict:
    try:
        response = requests.get(f"{BACKEND_URL}/api/scam-of-day", headers=_auth_headers(), timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_friendly(exc, "Không thể tải dữ liệu. Vui lòng thử lại sau.")
    return response.json()


# --- Scam Detective -------------------------------------------------------------

def load_detective_cases() -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/api/detective/cases", headers=_auth_headers(), timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_friendly(exc, "Không thể tải danh sách case. Vui lòng thử lại sau.")
    return response.json()


def load_detective_case(case_id: str) -> dict:
    try:
        response = requests.get(f"{BACKEND_URL}/api/detective/cases/{case_id}", headers=_auth_headers(), timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_friendly(exc, "Không thể tải case. Vui lòng thử lại sau.")
    return response.json()


def submit_detective_case(case_id: str, selected_signal_ids: list[str]) -> dict:
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/detective/cases/{case_id}/submit",
            headers=_auth_headers(),
            json={"selected_signal_ids": selected_signal_ids},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        _raise_friendly(exc, "Không thể chấm điểm. Vui lòng thử lại sau.")
    return response.json()


def record_remote_detective_attempt(case_id: str, correct_count: int, total_expected: int, xp_earned: int, result: dict) -> None:
    try:
        requests.post(
            f"{BACKEND_URL}/api/learning-progress/detective-attempts",
            json={
                "case_id": case_id,
                "correct_count": correct_count,
                "total_expected": total_expected,
                "xp_earned": xp_earned,
                "result": result,
            },
            headers=_auth_headers(),
            timeout=15,
        )
    except requests.RequestException:
        pass  # tinh nang phu, khong chan viec nop dap an


def load_remote_detective_attempts() -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/api/learning-progress/detective-attempts", headers=_auth_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []
