---

### FILE 2: `GUIDE.md`
*(File này là quy trình từng bước bạn nhập vào Cursor Composer)*

```markdown
# HƯỚNG DẪN THỰC HIỆN DỰ ÁN VỚI CURSOR

## BƯỚC 0: CHUẨN BỊ
1. Tạo thư mục `agri-agent-system`.
2. Mở bằng Cursor.
3. Tạo file `PROMPTS.md` và dán nội dung file prompts vào.

## BƯỚC 1: KHỞI TẠO MÔI TRƯỜNG (Giai đoạn 1)
*Mục tiêu: Cài đặt thư viện và JupyterLab.*
1. Nhấn **Ctrl + I** (Composer).
2. Gõ lệnh:
   "Dựa trên **GIAI ĐOẠN 1** trong `@PROMPTS.md`. Hãy:
   1. Tạo cấu trúc thư mục dự án (bao gồm `notebooks/`).
   2. Tạo file `requirements.txt` đầy đủ các thư viện cần thiết.
   3. Tạo file `.env.example`."
3. Mở Terminal (phím tắt `Ctrl + ~`), gõ lần lượt các lệnh sau để thiết lập môi trường:
   *   **Tạo môi trường ảo:**
       `python3 -m venv venv`
   *   **Kích hoạt môi trường (Windows):**
       `.\venv\Scripts\activate`
   *   **Kích hoạt môi trường (Mac/Linux):**
       `source venv/bin/activate`
4. Khi thấy terminal hiện chữ `(venv)` ở đầu dòng, chạy lệnh cài đặt:
   `pip install -r requirements.txt`

## BƯỚC 2: TOOL THU THẬP DỮ LIỆU (Giai đoạn 2)
1. Nhấn **Ctrl + I**.
2. Gõ lệnh:
   "Thực hiện **GIAI ĐOẠN 2** trong `@PROMPTS.md`.
   Tạo `src/tools/filter.py` và `src/tools/scraper.py`.
   Chú ý kỹ phần xử lý encoding bằng `charset_normalizer`."

## BƯỚC 3: XÂY DỰNG TRÍ THÔNG MINH (Giai đoạn 3 & 4)
1. Nhấn **Ctrl + I**.
2. Gõ lệnh:
   "Thực hiện **GIAI ĐOẠN 3** và **GIAI ĐOẠN 4** trong `@PROMPTS.md`.
   1. Tạo `src/models.py` định nghĩa AgriClaim.
   2. Tạo `src/agents/extractor.py` dùng Gemini Flash.
   3. Tạo `src/agents/resolver.py` cài đặt thuật toán Weighted Voting."

## BƯỚC 4: KẾT NỐI LUỒNG & GIAO DIỆN (Giai đoạn 5)
1. Nhấn **Ctrl + I**.
2. Gõ lệnh:
   "Thực hiện **GIAI ĐOẠN 5** trong `@PROMPTS.md`.
   1. Tạo `src/workflows/main.py` dùng LangGraph kết nối các node.
   2. Tạo `app.py` dùng Streamlit để hiển thị kết quả."

## BƯỚC 5: CHẠY THỬ & PHÂN TÍCH (Giai đoạn 6)
*Mục tiêu: Dùng JupyterLab để vẽ biểu đồ báo cáo.*
1. Mở Terminal, gõ: `jupyter lab`.
2. Trình duyệt sẽ mở ra. Tạo file `notebooks/analysis.ipynb`.
3. Quay lại Cursor Chat (Ctrl + L), gõ:
   "Tôi đang ở trong file `notebooks/analysis.ipynb`. Hãy viết code Python để:
   1. Giả lập một bộ dữ liệu kết quả (gồm nguồn tin, độ tin cậy, nội dung).
   2. Vẽ biểu đồ tròn phân bố nguồn tin (.gov.vn vs .edu.vn).
   3. Tính toán độ chính xác trung bình."
4. Copy code Cursor sinh ra dán vào Jupyter Notebook và nhấn Run (Shift + Enter).