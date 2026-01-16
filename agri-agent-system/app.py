from __future__ import annotations

"""
Ứng dụng Streamlit đơn giản cho Agri-Agent.

Chức năng:
- Cho phép người dùng nhập tên cây trồng (VD: "Lúa ST25").
- Gọi workflow LangGraph (Search -> Extract -> Resolve -> Writer).
- Hiển thị tóm tắt kết quả, danh sách claim đã hợp nhất và thông tin debug cơ bản.
"""

import os
from typing import Any, Dict, List

from dotenv import load_dotenv
import streamlit as st

from src.workflows.main import WorkflowState, run_agri_workflow


def _ensure_env_loaded() -> None:
    """
    Load biến môi trường từ file .env (nếu tồn tại).
    """
    # Chỉ load một lần
    if getattr(_ensure_env_loaded, "_loaded", False):
        return

    load_dotenv()
    setattr(_ensure_env_loaded, "_loaded", True)


def _render_summary(summary: str) -> None:
    """
    Hiển thị phần tóm tắt kết quả.
    """
    if not summary:
        st.info("Chưa có kết quả. Hãy nhập thông tin và bấm nút phân tích.")
        return
    st.markdown("### 📌 Kết quả tổng hợp")
    st.text(summary)


def _render_resolved_table(state: WorkflowState) -> None:
    """
    Hiển thị bảng các claim đã được resolver hợp nhất.
    """
    resolved = state.get("resolved_claims") or []
    if not resolved:
        st.warning("Chưa có ResolvedClaim nào (có thể do không trích xuất được claim từ các URL).")
        return

    rows: List[Dict[str, Any]] = []
    for rc in resolved:
        c = rc.gold_claim
        rows.append(
            {
                "Subject": c.subject,
                "Predicate": c.predicate,
                "Object": c.object,
                "Context": c.context,
                "Confidence": c.confidence,
                "Nguồn (ví dụ)": ", ".join(rc.support_urls[:3]),
                "Điểm cụm": rc.total_score,
            }
        )

    st.markdown("### 📊 Bảng tri thức đã hợp nhất")
    st.dataframe(rows, use_container_width=True)


def _render_debug_info(state: WorkflowState) -> None:
    """
    Hiển thị một số thông tin debug cơ bản (tùy chọn).
    """
    with st.expander("Chi tiết kỹ thuật / Debug", expanded=False):
        st.json(
            {
                "crop": state.get("crop"),
                "search_query": state.get("debug_info", {}).get("search_query"),
                "num_search_results": state.get("debug_info", {}).get("num_search_results"),
                "num_claims": state.get("debug_info", {}).get("num_claims"),
                "num_resolved_claims": state.get("debug_info", {}).get("num_resolved_claims"),
                "errors": state.get("debug_info", {}).get("errors"),
            }
        )


def main() -> None:
    """
    Entry point của ứng dụng Streamlit.
    """
    _ensure_env_loaded()

    st.set_page_config(
        page_title="Agri-Agent Demo",
        page_icon="🌾",
        layout="wide",
    )

    st.title("🌾 Agri-Agent – Phân tích tri thức nông nghiệp")
    st.markdown(
        "Nhập **tên giống cây trồng** hoặc **chủ đề nông nghiệp**, hệ thống sẽ:\n"
        "1. Tìm kiếm thông tin trên web (ưu tiên nguồn `.gov.vn`, `.edu.vn`).\n"
        "2. Trích xuất các *AgriClaim* từ nội dung trang.\n"
        "3. Hợp nhất và hiển thị kết quả đáng tin cậy cho bạn."
    )

    with st.sidebar:
        st.header("⚙️ Cấu hình")
        crop = st.text_input("Cây trồng / Chủ đề", value="Lúa ST25")
        custom_query = st.text_input(
            "Tùy chọn: Từ khóa tìm kiếm nâng cao",
            help="Nếu để trống, hệ thống sẽ tự sinh câu query phù hợp.",
        )

        max_info = st.markdown(
            "**Lưu ý:** Ứng dụng này phụ thuộc vào `GOOGLE_API_KEY` và kết nối mạng để hoạt động."
        )

        if not os.getenv("GOOGLE_API_KEY"):
            st.warning(
                "Biến môi trường `GOOGLE_API_KEY` chưa được thiết lập. "
                "Hãy tạo file `.env` hoặc export trước khi chạy để Extractor hoạt động.",
                icon="⚠️",
            )

        run_button = st.button("🚀 Phân tích", type="primary")

    if run_button:
        if not crop.strip():
            st.error("Vui lòng nhập tên cây trồng hoặc chủ đề.")
            return

        with st.spinner("Đang chạy workflow Agri-Agent (Search -> Extract -> Resolve -> Writer)..."):
            try:
                state = run_agri_workflow(crop=crop, initial_query=custom_query or None)
            except Exception as exc:
                st.error(f"Có lỗi xảy ra khi chạy workflow: {exc}")
                return

        # Kết quả chính
        _render_summary(state.get("summary", ""))
        _render_resolved_table(state)
        _render_debug_info(state)
    else:
        st.info("Nhập thông tin bên sidebar và bấm **🚀 Phân tích** để bắt đầu.")


if __name__ == "__main__":
    main()

