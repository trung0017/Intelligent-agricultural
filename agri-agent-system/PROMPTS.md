# PROMPTS.md - AGRI-AGENT MASTER PLAN

## 1. BỐI CẢNH DỰ ÁN (PROJECT CONTEXT)
*   **Tên đề tài:** Hệ thống phân tích dữ liệu nông nghiệp thông minh Multi-Agent (Agri-Agent) cho ĐBSCL.
*   **Mục tiêu:** Thu thập dữ liệu Web -> Trích xuất tri thức (Claims) -> Kiểm định mâu thuẫn (NLI) -> Xếp hạng tin cậy -> Cập nhật Wiki.
*   **Stack công nghệ (Low-cost & High-performance):**
    *   **Core:** Python 3.10+, LangGraph (Orchestrator).
    *   **LLM:** Google Gemini 1.5 Flash (ưu tiên vì rẻ & context dài) hoặc GPT-4o mini.
    *   **Search:** `duckduckgo-search` (miễn phí) hoặc `tavily-python` (nếu cần ổn định).
    *   **Scraping:** `trafilatura` (ưu tiên lấy text), `BeautifulSoup4` (fallback).
    *   **DB:** ChromaDB (Vector Store), SQLite (Metadata).

---

## PHẦN A: SYSTEM PROMPTS (TEMPLATES CHO AGENT)
*Đây là các "nhân cách" AI sẽ được nhúng vào code Python.*

### 1. EXTRACTION PROMPT (Trích xuất tri thức)
```text
Bạn là Chuyên gia Dữ liệu Nông nghiệp Việt Nam.
Nhiệm vụ: Trích xuất các khẳng định (Claims) từ văn bản về giống cây trồng/kỹ thuật canh tác.
Input Text: "{text}"

Yêu cầu Output định dạng JSON (AgriClaim):
{
  "subject": "Tên thực thể chính hóa (VD: Lúa ST25, Bệnh đạo ôn)",
  "predicate": "Thuộc tính (VD: Năng suất, Thời gian sinh trưởng, Khả năng chịu mặn)",
  "object": "Giá trị cụ thể bao gồm đơn vị (VD: 8.5 tấn/ha, 95-100 ngày)",
  "context": "Điều kiện áp dụng (VD: Vụ Đông Xuân, Vùng ven biển)",
  "confidence": "Độ tin cậy của mô hình (float 0.0 - 1.0)"
}
Lưu ý: Nếu không tìm thấy thông tin định lượng, trả về null.
```

### 2. NLI JUDGE PROMPT (Kiểm định mâu thuẫn)
```text
Bạn là Thẩm phán Logic (NLI Judge). Nhiệm vụ là so sánh một Mệnh đề Mới (New Claim) với Tri thức Cũ (Existing Knowledge).

Tri thức cũ: "{old_claim}"
Mệnh đề mới: "{new_claim}"

Hãy phân tích và trả về JSON:
{
  "relation": "SUPPORTED" (Trùng khớp ý nghĩa/số liệu) | "CONTRADICTED" (Mâu thuẫn số liệu/ý nghĩa) | "NEUTRAL" (Không liên quan),
  "difference_gap": "Độ lệch số liệu nếu có (VD: 10%)",
  "reasoning": "Giải thích ngắn gọn tại sao"
}

Quy tắc:
- Số liệu lệch < 5% xem là SUPPORTED.
- Đơn vị đo lường khác nhau cần quy đổi trước khi so sánh.
```

## PHẦN B: CODING INSTRUCTIONS (DÀNH CHO CURSOR)

*Hướng dẫn: Mở Composer (Ctrl+I), gõ "Thực hiện Giai đoạn X trong file @PROMPTS.md" để code.*

### GIAI ĐOẠN 1: THIẾT KẾ KIẾN TRÚC & MÔI TRƯỜNG (ARCHITECT)
Đóng vai trò là Kiến trúc sư Phần mềm.

1.  **Cấu trúc dự án:** Tạo cây thư mục chuẩn:
    *   `src/agents/`, `src/workflows/`, `src/tools/`, `src/utils/`.
    *   `notebooks/`: Chứa các file Jupyter Notebook (.ipynb) để thử nghiệm thuật toán và phân tích dữ liệu (Yêu cầu bắt buộc).
    *   `data/`: Chứa `chroma_db` và dataset.
2.  **Thư viện:** Tạo `requirements.txt` bao gồm:
    *   Core: `langgraph`, `langchain`, `langchain-google-genai`, `pydantic`.
    *   Data/Web: `trafilatura`, `beautifulsoup4`, `duckduckgo-search`, `charset_normalizer`.
    *   Analysis (Jupyter): `jupyterlab`, `pandas`, `matplotlib`, `seaborn`.
    *   App: `streamlit`, `python-dotenv`.
3.  **Thiết kế LangGraph:** Vẽ mã PlantUML cho luồng: Search -> Extract -> Judge -> Resolve -> Writer.

### GIAI ĐOẠN 2: CÔNG CỤ THU THẬP DỮ LIỆU (BACKEND DEV)
Đóng vai trò là Senior Python Developer. Viết file `src/tools/scraper.py` và `src/tools/filter.py`.

**Yêu cầu 1: Domain Filter (Xếp hạng nguồn tin)**
*   Viết hàm `calculate_trust_score(url)`:
    *   Domain `.gov.vn`: 1.0 điểm.
    *   Domain `.edu.vn`: 0.9 điểm.
    *   Báo chí chính thống: 0.8 điểm.
    *   Khác: 0.5 điểm.

**Yêu cầu 2: Advanced Scraper (Xử lý Web Việt Nam)**
*   Sử dụng `trafilatura` để lấy main text sạch.
*   **Quan trọng:** Dùng thư viện `charset_normalizer` để tự động phát hiện và decode các bảng mã cũ (Windows-1258, VNI...) thường gặp ở web nông nghiệp địa phương.

### GIAI ĐOẠN 3: ENGINE TRÍCH XUẤT (AI ENGINEER)
Đóng vai trò là AI Engineer. Viết file `src/agents/extractor.py` và `src/models.py`.

1.  Định nghĩa Pydantic Object `AgriClaim` (như mẫu Phần A).
2.  Viết hàm `extract_claims` sử dụng Gemini 1.5 Flash.
3.  Kết hợp với Scraper từ Giai đoạn 2 để biến URL thành List[AgriClaim].

### GIAI ĐOẠN 4: THUẬT TOÁN GIẢI QUYẾT MÂU THUẪN (DATA SCIENTIST)
Đóng vai trò là Data Scientist. Viết file `src/agents/resolver.py`.
*Yêu cầu khoa học cao: Xử lý khi nhiều nguồn nói khác nhau về cùng 1 vấn đề.*

**Thuật toán Weighted Voting:**
1.  **Clustering:** Gom nhóm các giá trị xấp xỉ nhau (VD: 8.0 tấn, 8.1 tấn là 1 nhóm).
2.  **Scoring:** Tính điểm nhóm = Tổng (Trust Score của nguồn * Hệ số thời gian).
    *   Hệ số thời gian: Năm hiện tại (1.2), cũ hơn (1.0).
3.  **Decision:** Chọn nhóm điểm cao nhất làm "Gold Standard".

### GIAI ĐOẠN 5: ORCHESTRATION & APP (LEAD DEV)
Đóng vai trò là Lead Developer.

1.  **Workflow (`src/workflows/main.py`):** Dùng LangGraph kết nối các node. Cài đặt vòng lặp tự sửa (Nếu không tìm thấy thông tin -> Search lại với từ khóa mở rộng).
2.  **App (`app.py`):** Giao diện Streamlit đơn giản cho người dùng nhập cây trồng và nhận kết quả phân tích.

### GIAI ĐOẠN 6: PHÂN TÍCH & BÁO CÁO (RESEARCHER)
Đóng vai trò là Nghiên cứu viên. Sử dụng JupyterLab.

1.  Tạo file `notebooks/analysis.ipynb`.
2.  Viết code load dữ liệu log từ quá trình chạy Agent.
3.  Vẽ biểu đồ:
    *   Phân bố nguồn tin (Pie Chart: Gov vs Edu vs Others).
    *   Độ chính xác (Confusion Matrix) so với dữ liệu chuẩn.