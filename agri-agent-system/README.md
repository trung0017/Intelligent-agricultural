# 🌾 Agri-Agent System - Hướng dẫn chạy project

> Hệ thống Multi-Agent phân tích dữ liệu nông nghiệp thông minh cho ĐBSCL

## 📋 Mục lục

1. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
2. [Cài đặt nhanh](#cài-đặt-nhanh)
3. [Cấu hình](#cấu-hình)
4. [Chạy ứng dụng](#chạy-ứng-dụng)
5. [Sử dụng](#sử-dụng)
6. [Test](#test)
7. [Xử lý lỗi](#xử-lý-lỗi)

---

## 🖥️ Yêu cầu hệ thống

- **Python**: 3.10+ (khuyến nghị 3.11+)
- **Hệ điều hành**: macOS, Linux, Windows
- **RAM**: Tối thiểu 4GB (khuyến nghị 8GB+)
- **Kết nối Internet**: Cần thiết cho API calls và web scraping

---

## ⚡ Cài đặt nhanh

### Bước 1: Clone hoặc di chuyển vào thư mục project

```bash
cd agri-agent-system
```

### Bước 2: Tạo virtual environment

```bash
# macOS/Linux
python3 -m venv venv

# Windows
python -m venv venv
```

### Bước 3: Kích hoạt virtual environment

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

Bạn sẽ thấy `(venv)` ở đầu dòng terminal khi đã kích hoạt thành công.

### Bước 4: Cài đặt dependencies

```bash
# Nâng cấp pip
pip install --upgrade pip

# Cài đặt tất cả packages
pip install -r requirements.txt
```

**Lưu ý cho Mac M4 (ARM):**
```bash
# Nếu gặp lỗi build, cài thêm build tools
brew install cmake pkg-config
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

---

## ⚙️ Cấu hình

### Bước 1: Tạo file `.env`

```bash
# Copy từ template
cp env.example .env
```

### Bước 2: Lấy Google API Key

1. Truy cập: https://makersuite.google.com/app/apikey
2. Đăng nhập với tài khoản Google
3. Tạo API key mới
4. Copy API key

### Bước 3: Cấu hình `.env`

Mở file `.env` và thêm API key:

```env
# LLM & SEARCH KEYS
GOOGLE_API_KEY=your-google-api-key-here
OPENAI_API_KEY=
TAVILY_API_KEY=

# LANGSMITH / LANGCHAIN (OPTIONAL)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=

# APP CONFIG
AGRI_AGENT_ENV=dev
STREAMLIT_SERVER_PORT=8501
```

**Lưu ý:** Thay `your-google-api-key-here` bằng API key thực tế của bạn.

### Bước 3: Tạo thư mục cần thiết

```bash
mkdir -p data/chroma_db data/judge_cache notebooks
```

---

## 🚀 Chạy ứng dụng

### Cách 1: Chạy Streamlit UI (Khuyến nghị)

```bash
# Đảm bảo venv đã kích hoạt
source venv/bin/activate  # macOS/Linux
# hoặc
venv\Scripts\activate     # Windows

# Chạy ứng dụng
streamlit run app.py
```

Ứng dụng sẽ tự động mở trình duyệt tại: **http://localhost:8501**

### Cách 2: Chạy từ Python script

```bash
# Đảm bảo venv đã kích hoạt
source venv/bin/activate

# Chạy trực tiếp
python app.py
```

### Cách 3: Sử dụng API programmatically

```python
from src.workflows.main import run_agri_workflow

# Chạy workflow
result = run_agri_workflow(crop="Lúa ST25")

# Xem kết quả
print(result["summary"])
print(f"Số claims: {len(result.get('claims', []))}")
print(f"Số resolved claims: {len(result.get('resolved_claims', []))}")
```

---

## 📖 Sử dụng

### Giao diện Streamlit

1. **Mở trình duyệt** tại http://localhost:8501
2. **Nhập tên cây trồng** vào ô "Cây trồng / Chủ đề" (ví dụ: "Lúa ST25")
3. **Tùy chọn**: Nhập từ khóa tìm kiếm nâng cao
4. **Click nút "🚀 Phân tích"**
5. **Xem kết quả**:
   - Kết quả tổng hợp (summary)
   - Bảng tri thức đã hợp nhất (resolved claims)
   - Chi tiết kỹ thuật / Debug (mở rộng)

### Ví dụ sử dụng

**Input:**
- Cây trồng: `Lúa ST25`
- Từ khóa: (để trống)

**Output:**
- Danh sách claims về năng suất, thời gian sinh trưởng, khả năng chịu mặn...
- Resolved claims với trust score và nguồn dẫn chứng
- Summary tổng hợp

---

## 🧪 Test

### Test 1: Trích xuất claims

```bash
# Đảm bảo venv đã kích hoạt
source venv/bin/activate

# Chạy test
python test_claim_extraction.py
```

**Kỳ vọng:** Trích xuất được 10-15+ claims từ bài viết mẫu.

### Test 2: Phát hiện mâu thuẫn

```bash
# Đảm bảo venv đã kích hoạt
source venv/bin/activate

# Chạy test
python test_contradiction_detection.py
```

**Kỳ vọng:** Phát hiện được contradictions giữa các claims.

### Test 3: Kiểm tra import modules

```bash
python -c "from src.models import AgriClaim; print('✅ Models OK')"
python -c "from src.agents.extractor import extract_claims_from_text; print('✅ Extractor OK')"
python -c "from src.agents.judge import judge_claims; print('✅ Judge OK')"
python -c "from src.agents.resolver import group_and_resolve_claims; print('✅ Resolver OK')"
python -c "from src.workflows.main import run_agri_workflow; print('✅ Workflow OK')"
```

---

## 🔧 Xử lý lỗi

### Lỗi: "GOOGLE_API_KEY chưa được thiết lập"

**Nguyên nhân:** File `.env` chưa có hoặc API key chưa được thiết lập.

**Giải pháp:**
```bash
# Kiểm tra file .env
cat .env | grep GOOGLE_API_KEY

# Nếu trống, thêm vào .env
echo 'GOOGLE_API_KEY=your-key-here' >> .env

# Hoặc export trực tiếp (tạm thời)
export GOOGLE_API_KEY="your-key-here"
```

### Lỗi: "ModuleNotFoundError: No module named 'xxx'"

**Nguyên nhân:** Package chưa được cài đặt hoặc venv chưa kích hoạt.

**Giải pháp:**
```bash
# Đảm bảo venv đã kích hoạt
source venv/bin/activate  # macOS/Linux

# Cài lại package
pip install -r requirements.txt

# Hoặc cài package cụ thể
pip install xxx
```

### Lỗi: "429 RESOURCE_EXHAUSTED" (Quota exceeded)

**Nguyên nhân:** Đã vượt quá quota API của Google.

**Giải pháp:**
- Code đã có retry logic tự động (chờ 15-30 giây)
- Kiểm tra quota tại: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
- Nâng cấp plan nếu cần

### Lỗi: "Port 8501 already in use"

**Nguyên nhân:** Port đã được sử dụng bởi process khác.

**Giải pháp:**
```bash
# Tìm process đang dùng port
lsof -i :8501  # macOS/Linux
netstat -ano | findstr :8501  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Hoặc đổi port
streamlit run app.py --server.port 8502
```

### Lỗi: "Failed building wheel" (Mac M4)

**Nguyên nhân:** Thiếu build tools cho ARM architecture.

**Giải pháp:**
```bash
# Cài đặt build tools
brew install cmake pkg-config rust

# Nâng cấp pip và build tools
pip install --upgrade pip setuptools wheel

# Cài lại
pip install -r requirements.txt
```

### Lỗi: "DuckDuckGo search không trả về kết quả"

**Nguyên nhân:** Query tiếng Việt có thể không có kết quả.

**Giải pháp:**
- Code đã có fallback queries tự động
- Thử query tiếng Anh: "ST25 rice variety Vietnam"
- Kiểm tra kết nối Internet

---

## 📊 Cấu trúc project

```
agri-agent-system/
├── app.py                    # Streamlit UI chính
├── requirements.txt          # Dependencies
├── env.example              # Template biến môi trường
├── README.md                # File này
├── PROMPTS.md               # System prompts & hướng dẫn
├── PLAN.md                  # Kế hoạch triển khai
├── GUIDE.md                 # Hướng dẫn sử dụng Cursor
├── src/
│   ├── models.py            # Pydantic models (AgriClaim)
│   ├── agents/
│   │   ├── extractor.py     # Trích xuất claims từ text/URL
│   │   ├── judge.py         # Phát hiện mâu thuẫn (NLI Judge)
│   │   └── resolver.py      # Hợp nhất claims (Weighted Voting)
│   ├── tools/
│   │   ├── scraper.py       # Web scraping với encoding detection
│   │   └── filter.py        # Tính trust score theo domain
│   └── workflows/
│       └── main.py          # LangGraph workflow chính
├── data/
│   ├── chroma_db/           # Vector database (chưa sử dụng)
│   └── judge_cache/        # Cache judge results (pickle files)
├── notebooks/               # Jupyter notebooks (phân tích)
└── test_*.py               # Test scripts
```

---

## 🎯 Workflow hoạt động

```
1. Search Node
   ↓ (Tìm kiếm URL từ DuckDuckGo)
2. Extract Node
   ↓ (Trích xuất claims từ mỗi URL)
3. Resolve Node
   ↓ (Hợp nhất claims bằng Weighted Voting)
4. Writer Node
   ↓ (Tạo summary)
5. Kết quả cuối cùng
```

---

## 📝 Ví dụ sử dụng nâng cao

### Sử dụng Extractor trực tiếp

```python
from src.agents.extractor import extract_claims_from_url, extract_claims_from_text

# Trích xuất từ URL
claims = extract_claims_from_url("https://example.com/article")

# Trích xuất từ text
text = "Lúa ST25 đạt năng suất 8.5 tấn/ha..."
claims = extract_claims_from_text(text)
```

### Sử dụng Judge để phát hiện mâu thuẫn

```python
from src.agents.judge import judge_claims
from src.models import AgriClaim

claim1 = AgriClaim(
    subject="Lúa ST25",
    predicate="Giải thưởng",
    object="Giải nhất",
    confidence=0.9
)

claim2 = AgriClaim(
    subject="Lúa ST25",
    predicate="Giải thưởng",
    object="Giải khuyến khích",
    confidence=0.9
)

result = judge_claims(claim1, claim2)
print(result["relation"])  # CONTRADICTED
```

### Sử dụng Resolver để hợp nhất claims

```python
from src.agents.resolver import group_and_resolve_claims
from src.models import AgriClaim

# Danh sách claims từ nhiều nguồn
claims = [
    AgriClaim(subject="Lúa ST25", predicate="Năng suất", object="8.5 tấn/ha", source_url="url1"),
    AgriClaim(subject="Lúa ST25", predicate="Năng suất", object="8.6 tấn/ha", source_url="url2"),
    # ...
]

# Hợp nhất
resolved = group_and_resolve_claims(claims)
for rc in resolved:
    print(f"{rc.gold_claim.object} (Score: {rc.total_score})")
```

---

## 🔗 Tài liệu tham khảo

- [PROMPTS.md](./PROMPTS.md) - System prompts và hướng dẫn chi tiết
- [PLAN.md](./PLAN.md) - Kế hoạch triển khai
- [GUIDE.md](./GUIDE.md) - Hướng dẫn sử dụng Cursor Composer

---

## 💡 Tips

1. **Tối ưu API calls**: Judge results được cache tự động trong `data/judge_cache/`
2. **Xử lý văn bản dài**: Extractor tự động chunking cho văn bản > 3000 ký tự
3. **Retry logic**: Tự động retry khi gặp lỗi quota (429)
4. **Trust score**: Ưu tiên nguồn `.gov.vn` > `.edu.vn` > báo chí > khác

---

## 📞 Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra log trong terminal
2. Xem phần [Xử lý lỗi](#xử-lý-lỗi)
3. Kiểm tra file `.env` và `GOOGLE_API_KEY`
4. Chạy test scripts để kiểm tra từng module

---

**Chúc bạn sử dụng thành công! 🎉**
