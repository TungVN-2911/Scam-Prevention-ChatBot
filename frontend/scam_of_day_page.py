import streamlit as st

from api_client import ApiError, load_detective_cases, load_scam_of_day
from detective_page import start_detective_case


def render_scam_of_day() -> None:
    st.header("🛡️ Scam of the Day")
    try:
        data = load_scam_of_day()
    except ApiError as exc:
        st.error(str(exc))
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
            except ApiError as exc:
                st.error(str(exc))
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
