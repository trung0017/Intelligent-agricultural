# PLAN.md - KẾ HOẠCH TRIỂN KHAI HỆ THỐNG PHÂN TÍCH DỮ LIỆU NÔNG NGHIỆP THÔNG MINH

## 1. TỔNG QUAN DỰ ÁN
- **Tên đề tài:** Xây dựng hệ thống phân tích dữ liệu thông minh dựa trên các giải thuật máy học (Ứng dụng cho nông nghiệp ĐBSCL).
- **Mục tiêu:** Xây dựng hệ thống Multi-Agent có khả năng thu thập, trích xuất, kiểm định và giải quyết mâu thuẫn dữ liệu từ Internet để xây dựng cơ sở tri thức (Wiki) nông nghiệp.

## 2. KIẾN TRÚC KỸ THUẬT (TECH STACK)
- **Ngôn ngữ:** Python 3.10+.
- **Framework Orchestration:** LangChain / LangGraph.
- **LLM Provider:** Google Generative AI (Gemini) hoặc OpenAI (GPT-4o mini).
- **Search Engine:** 
  - `duckduckgo-search` (Python Lib - Miễn phí).
  - Google Custom Search API (Giới hạn domain .gov.vn/.edu.vn).
- **Database:**
  - Vector DB: ChromaDB (Local).
  - Relational DB: SQLite (Lưu lịch sử, user, cache).
  - Caching: Redis hoặc File-based Caching (pickle).
- **Frontend:** Streamlit.

## 3. LỘ TRÌNH THỰC HIỆN CHI TIẾT

| Giai đoạn | Module | Nhiệm vụ chi tiết & Yêu cầu kỹ thuật |
| :--- | :--- | :--- |
| **GĐ 1: Khởi tạo** | **Setup** | - Thiết lập môi trường Python, Git. <br> - Cài đặt thư viện. <br> - Thiết kế sơ đồ kiến trúc Multi-Agent. |
| **GĐ 2: Thu thập** | **Crawler Agent** | - Tích hợp `duckduckgo-search`. <br> - Xây dựng bộ lọc domain (Whitelist: .gov.vn, .edu.vn). <br> - Làm sạch HTML (xóa quảng cáo, script) chỉ giữ text. |
| **GĐ 3: Trích xuất** | **Extractor Agent** | - Dùng LLM trích xuất thông tin dạng JSON (Claims). <br> - Trường dữ liệu: Subject (Giống lúa), Predicate (Năng suất), Value (số liệu). |
| **GĐ 4: Lưu trữ & Đệm** | **Storage & Cache** | - Thiết lập SQLite để lưu dữ liệu thô. <br> - Cài đặt Caching để không gọi API 2 lần cho cùng 1 URL (Tiết kiệm tiền). |
| **GĐ 5: Kiểm định** | **Judge Agent** | - Xây dựng cơ chế "LLM-as-a-Judge". <br> - So sánh Claim mới vs Knowledge Base cũ. <br> - Nhãn: SUPPORTED, CONTRADICTED, NEUTRAL. |
| **GĐ 6: Xử lý mâu thuẫn**| **Resolver Logic** | - Thuật toán Rule-based: Ưu tiên nguồn Gov > Edu > Com. <br> - Ưu tiên năm xuất bản mới hơn. <br> - Tự động quyết định giữ/thay thế thông tin. |
| **GĐ 7: Giao diện** | **UI/UX** | - Xây dựng Web App bằng Streamlit. <br> - Cho phép nhập câu hỏi -> Hiển thị câu trả lời tổng hợp + Nguồn dẫn chứng. |
| **GĐ 8: Đánh giá** | **Benchmark** | - Tạo bộ Gold Standard (50 mẫu). <br> - Chạy script tính Precision/Recall/F1-Score. |

## 4. QUY TẮC CODE (CODING CONVENTIONS)
- **Docstring:** Mọi hàm phải có docstring giải thích Input/Output.
- **Type Hinting:** Sử dụng Python Type Hints (VD: `def func(text: str) -> dict:`).
- **Error Handling:** Luôn dùng try/except cho các tác vụ gọi API hoặc Network.
- **Environment:** Tuyệt đối không hard-code API Key. Dùng file `.env`.
