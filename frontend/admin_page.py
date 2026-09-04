import streamlit as st

from api_client import ApiError, approve_pending_report, load_pending_reports, reject_pending_report


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def render_admin() -> None:
    st.header("🛡️ Duyệt báo cáo tình huống lạ")
    st.caption(
        "Các tình huống người dùng mô tả mà hệ thống chưa xác định khớp với hình thức lừa đảo nào đã biết. "
        "Chỉ duyệt khi bạn đã tự xác minh bằng nguồn đáng tin cậy — hệ thống không tự sinh nội dung."
    )

    try:
        reports = load_pending_reports()
    except ApiError as exc:
        st.error(str(exc))
        return

    pending = [r for r in reports if r["status"] == "pending_review"]
    # Bao cao bi bao lai nhieu lan (cung noi dung sau chuan hoa) len truoc - tin hieu de uu tien duyet.
    pending.sort(key=lambda r: r.get("count", 1), reverse=True)
    if not pending:
        st.success("Không có báo cáo nào đang chờ duyệt.")
    for report in pending:
        count = report.get("count", 1)
        count_label = f" · đã báo cáo {count} lần" if count > 1 else ""
        with st.expander(
            f"{report['id']} · điểm tương đồng cao nhất: {report['top_score']}{count_label} · {report['reported_at']}"
        ):
            st.markdown(f"**Nội dung người dùng mô tả:**\n\n{report['text']}")
            st.divider()

            with st.form(f"approve_form_{report['id']}"):
                st.markdown("**Điền thông tin hình thức lừa đảo đã xác minh:**")
                slug = st.text_input("Slug (định danh ngắn, không dấu, vd: fake-bank-otp)", key=f"slug_{report['id']}")
                name = st.text_input("Tên hình thức lừa đảo", key=f"name_{report['id']}")
                category = st.selectbox(
                    "Category", ["scams", "prevention", "recovery", "regulations"], key=f"cat_{report['id']}"
                )
                scenario = st.text_area("Kịch bản", key=f"scenario_{report['id']}", value=report["text"])
                warning_signs = st.text_area(
                    "Dấu hiệu cảnh báo (mỗi dòng 1 dấu hiệu)", key=f"warn_{report['id']}"
                )
                prevention = st.text_area("Cách phòng ngừa (mỗi dòng 1 ý)", key=f"prev_{report['id']}")
                if_victim = st.text_area("Nếu đã là nạn nhân (mỗi dòng 1 bước)", key=f"victim_{report['id']}")

                st.caption(
                    "⚠️ **Về nguồn**: nếu hình thức này đã có bài báo/cảnh báo chính thức, điền nguồn đó bên dưới. "
                    "Nếu đây thực sự là hình thức **MỚI** chưa ai công khai viết về nó, đừng bịa nguồn — hãy ghi rõ "
                    "cách bạn tự xác minh vào ô 'tên tổ chức' (vd: 'Xác minh nội bộ — đối chiếu cảnh báo ngân hàng X "
                    "ngày Y'). Nếu **không xác minh được** từ bất kỳ nguồn nào ngoài lời kể của người dùng, nên bấm "
                    "**Từ chối** thay vì duyệt — dữ liệu không truy vết được sẽ làm hỏng chính cơ chế chống bịa của hệ thống."
                )
                source_org = st.text_input(
                    "Nguồn — tên tổ chức",
                    key=f"src_org_{report['id']}",
                    help="Có thể là 1 tổ chức/báo chí thật, hoặc ghi rõ cách bạn tự xác minh nếu chưa có nguồn công khai.",
                )
                source_title = st.text_input(
                    "Nguồn — tiêu đề bài viết (để trống nếu không có bài viết công khai)",
                    key=f"src_title_{report['id']}",
                )
                source_url = st.text_input(
                    "Nguồn — URL (để trống nếu không có bài viết công khai)", key=f"src_url_{report['id']}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    approve_clicked = st.form_submit_button("✅ Duyệt", use_container_width=True)
                with col2:
                    reject_clicked = st.form_submit_button("❌ Từ chối", use_container_width=True)

            if approve_clicked:
                if not slug.strip() or not name.strip():
                    st.error("Cần điền ít nhất Slug và Tên hình thức lừa đảo.")
                else:
                    pattern = {
                        "slug": slug.strip(),
                        "name": name.strip(),
                        "category": category,
                        "scenario": scenario.strip(),
                        "warning_signs": _split_lines(warning_signs),
                        "prevention": _split_lines(prevention),
                        "if_victim": _split_lines(if_victim),
                        "source": {
                            k: v
                            for k, v in {
                                "organization": source_org.strip(),
                                "title": source_title.strip(),
                                "url": source_url.strip(),
                            }.items()
                            if v
                        },
                    }
                    try:
                        approve_pending_report(report["id"], pattern)
                    except ApiError as exc:
                        st.error(str(exc))
                    else:
                        st.success(f"Đã duyệt và đưa '{name}' vào knowledge base (đã upsert Pinecone).")
                        st.rerun()

            if reject_clicked:
                try:
                    reject_pending_report(report["id"], "")
                except ApiError as exc:
                    st.error(str(exc))
                else:
                    st.info("Đã từ chối báo cáo này.")
                    st.rerun()

    reviewed = [r for r in reports if r["status"] != "pending_review"]
    if reviewed:
        st.divider()
        st.markdown("#### Đã xử lý gần đây")
        for report in reviewed:
            icon = "✅" if report["status"] == "approved" else "❌"
            st.caption(f"{icon} {report['id']} — {report['status']} — {report['text'][:80]}")
