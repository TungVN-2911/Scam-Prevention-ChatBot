"""Man hinh Scam Detective: chon case, lam bai, xem ket qua + lich su."""

from datetime import datetime

import requests
import streamlit as st

from api_client import (
    add_remote_xp,
    load_detective_case,
    load_detective_cases,
    load_remote_detective_attempts,
    record_remote_detective_attempt,
    submit_detective_case,
)

DIFFICULTY_LABELS = {"easy": "🟢 Dễ", "medium": "🟡 Trung bình", "hard": "🔴 Khó"}


def start_detective_case(case_id: str) -> None:
    st.session_state.detective_case = load_detective_case(case_id)
    st.session_state.detective_stage = "case"
    st.session_state.detective_result = None


def render_detective_signal_review(signals: list[dict], selected_ids, expected_ids, explanations: dict) -> None:
    """Hien trang thai (dung/thieu/thua) + giai thich cho tung dau hieu -
    dung chung cho man ket qua vua nop VA man xem lai lich su."""
    selected = set(selected_ids)
    expected = set(expected_ids)
    for signal in signals:
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
        st.caption(explanations.get(sid, ""))


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
            st.error(f"Không thể tải danh sách case. Chi tiết lỗi: {exc}")
            return
        for case in cases:
            label = f"{DIFFICULTY_LABELS.get(case['difficulty'], case['difficulty'])} — {case['title']}"
            if st.button(label, key=f"case_{case['id']}", use_container_width=True):
                try:
                    start_detective_case(case["id"])
                except requests.RequestException as exc:
                    st.error(f"Không thể tải case. Chi tiết lỗi: {exc}")
                else:
                    st.rerun()

        st.divider()
        st.markdown("#### 📜 Lịch sử làm case gần đây")
        attempts = load_remote_detective_attempts()
        if not attempts:
            st.caption("Chưa có lượt làm case nào.")
        else:
            case_lookup = {c["id"]: c for c in cases}
            case_cache: dict[str, dict | None] = {}
            for attempt in attempts:
                case_summary = case_lookup.get(attempt["case_id"])
                title = case_summary["title"] if case_summary else attempt["case_id"]
                difficulty_label = DIFFICULTY_LABELS.get(
                    case_summary["difficulty"], case_summary["difficulty"]
                ) if case_summary else ""
                try:
                    time_str = datetime.fromisoformat(attempt["created_at"]).strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    time_str = attempt["created_at"]
                summary = (
                    f"{difficulty_label} {title} — {attempt['correct_count']}/{attempt['total_expected']} "
                    f"(+{attempt['xp_earned']} XP) · {time_str}"
                )
                with st.expander(summary):
                    if attempt["case_id"] not in case_cache:
                        try:
                            case_cache[attempt["case_id"]] = load_detective_case(attempt["case_id"])
                        except requests.RequestException as exc:
                            case_cache[attempt["case_id"]] = None
                            st.error(f"Không thể tải lại case để xem giải thích. Chi tiết lỗi: {exc}")
                    case_detail = case_cache[attempt["case_id"]]
                    if case_detail is not None:
                        st.markdown(case_detail["scenario"])
                        result = attempt["result"]
                        render_detective_signal_review(
                            case_detail["signals"],
                            result.get("selected_signal_ids", []),
                            result.get("expected_signals", []),
                            result.get("explanations", {}),
                        )

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
                st.error(f"Không thể chấm điểm. Chi tiết lỗi: {exc}")
            else:
                st.session_state.detective_result = result
                st.session_state.detective_selected = selected
                # XP thuoc Learning Progress, doc lap voi conversation session -
                # persist ngay lap tuc, KHONG cho vao session_state truoc khi
                # biet chac da luu thanh cong (database la source of truth).
                new_total_xp = add_remote_xp(result["xp"])
                record_remote_detective_attempt(
                    case["id"],
                    result["correct_count"],
                    result["total_expected"],
                    result["xp"],
                    {
                        "selected_signal_ids": selected,
                        "expected_signals": result["expected_signals"],
                        "explanations": result["explanations"],
                    },
                )
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
        render_detective_signal_review(
            case["signals"], st.session_state.detective_selected, result["expected_signals"], result["explanations"]
        )

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
