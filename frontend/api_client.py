"""Toan bo ham goi HTTP toi backend FastAPI. Khong chua logic hien thi
Streamlit - cac module *_page.py goi ham o day roi tu render UI."""

import os

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


# --- Chat -------------------------------------------------------------------

def post_chat_message(message: str, history: list[dict]) -> dict:
    response = requests.post(
        f"{BACKEND_URL}/api/chat",
        json={"message": message, "history": history},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


# --- Conversation session (lazy creation) ------------------------------------

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


# --- Learning Progress (XP) --------------------------------------------------

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


# --- Quiz ---------------------------------------------------------------------

def load_quiz(topic: str) -> list[dict]:
    response = requests.get(f"{BACKEND_URL}/api/quiz", params={"topic": topic}, timeout=30)
    response.raise_for_status()
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
            timeout=15,
        )
    except requests.RequestException:
        pass  # lich su lam bai la tinh nang phu, khong lam gian doan viec nop bai


def load_remote_quiz_attempts() -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/api/learning-progress/quiz-attempts", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


# --- Scam of the Day ----------------------------------------------------------

def load_scam_of_day() -> dict:
    response = requests.get(f"{BACKEND_URL}/api/scam-of-day", timeout=30)
    response.raise_for_status()
    return response.json()


# --- Scam Detective -------------------------------------------------------------

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
            timeout=15,
        )
    except requests.RequestException:
        pass  # lich su lam case la tinh nang phu, khong lam gian doan viec nop dap an


def load_remote_detective_attempts() -> list[dict]:
    try:
        response = requests.get(f"{BACKEND_URL}/api/learning-progress/detective-attempts", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []
