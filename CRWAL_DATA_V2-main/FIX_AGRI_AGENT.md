# 🔧 Sửa lỗi "Agri-Agent không khả dụng"

## ❌ Lỗi hiện tại

```
No module named 'langchain_google_genai'
```

## 🔍 Nguyên nhân

WikiNongSan đang tích hợp với Agri-Agent System nhưng virtual environment của WikiNongSan chưa có các dependencies cần thiết.

## ✅ Giải pháp

### Cách 1: Cài đặt dependencies vào venv của WikiNongSan (Khuyến nghị)

```bash
# 1. Di chuyển vào thư mục WikiNongSan
cd "/Users/dangthanhtrung/Academics/NCKH/Xây dựng hệ thống phân tích dữ liệu thông minh dựa trên các giải thuật máy học/src/CRWAL_DATA_V2-main"

# 2. Kích hoạt virtual environment
source venv/bin/activate

# 3. Cài đặt các dependencies của Agri-Agent
pip install langgraph>=0.2.0
pip install langchain>=0.3.0
pip install langchain-google-genai>=2.0.0
pip install pydantic>=2.0.0
pip install trafilatura>=1.6.0
pip install ddgs>=1.0.0
pip install charset-normalizer>=3.0.0
pip install chromadb>=0.5.0

# Hoặc cài tất cả cùng lúc
pip install langgraph langchain langchain-google-genai pydantic trafilatura ddgs charset-normalizer chromadb
```

### Cách 2: Cài đặt từ requirements.txt của Agri-Agent

```bash
# 1. Di chuyển vào thư mục WikiNongSan
cd "/Users/dangthanhtrung/Academics/NCKH/Xây dựng hệ thống phân tích dữ liệu thông minh dựa trên các giải thuật máy học/src/CRWAL_DATA_V2-main"

# 2. Kích hoạt virtual environment
source venv/bin/activate

# 3. Cài đặt từ requirements.txt của agri-agent-system
pip install -r ../agri-agent-system/requirements.txt
```

### Cách 3: Cập nhật requirements.txt của WikiNongSan

Thêm các dependencies vào `requirements.txt` của WikiNongSan:

```bash
# Mở file requirements.txt
nano requirements.txt
```

Thêm vào cuối file:

```txt
# Agri-Agent dependencies
langgraph>=0.2.0
langchain>=0.3.0
langchain-google-genai>=2.0.0
pydantic>=2.0.0
trafilatura>=1.6.0
ddgs>=1.0.0
charset-normalizer>=3.0.0
chromadb>=0.5.0
```

Sau đó cài đặt:

```bash
pip install -r requirements.txt
```

## 🔑 Cấu hình GOOGLE_API_KEY

Sau khi cài đặt dependencies, cần cấu hình API key:

```bash
# 1. Tạo file .env (nếu chưa có)
cd "/Users/dangthanhtrung/Academics/NCKH/Xây dựng hệ thống phân tích dữ liệu thông minh dựa trên các giải thuật máy học/src/CRWAL_DATA_V2-main"
touch .env

# 2. Thêm GOOGLE_API_KEY vào .env
echo 'GOOGLE_API_KEY=your-api-key-here' >> .env

# Hoặc chỉnh sửa bằng editor
nano .env
```

Lấy API key tại: https://makersuite.google.com/app/apikey

## ✅ Kiểm tra sau khi cài đặt

```bash
# 1. Kích hoạt venv
source venv/bin/activate

# 2. Test import
python -c "from langchain_google_genai import ChatGoogleGenerativeAI; print('✅ OK')"

# 3. Test Agri-Agent integration
python -c "from validator import AGRI_AGENT_AVAILABLE, IMPORT_ERROR; print(f'Agri-Agent: {AGRI_AGENT_AVAILABLE}, Error: {IMPORT_ERROR}')"
```

## 🚀 Khởi động lại server

```bash
# Dừng server hiện tại (Ctrl+C)
# Sau đó khởi động lại
python app.py
```

Truy cập: http://localhost:8000/admin/dashboard

## 📝 Lưu ý

1. **Virtual environment riêng**: WikiNongSan và Agri-Agent có thể dùng chung dependencies nhưng nên giữ venv riêng để tránh conflict
2. **GOOGLE_API_KEY**: Cần thiết cho Agri-Agent hoạt động
3. **Đường dẫn**: Đảm bảo `agri-agent-system` nằm cùng cấp với `CRWAL_DATA_V2-main`

## 🐛 Nếu vẫn lỗi

1. Kiểm tra đường dẫn agri-agent-system:
   ```bash
   ls ../agri-agent-system
   ```

2. Kiểm tra GOOGLE_API_KEY:
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GOOGLE_API_KEY'))"
   ```

3. Kiểm tra import trực tiếp:
   ```bash
   python -c "import sys; sys.path.insert(0, '../agri-agent-system'); from src.models import AgriClaim; print('✅ OK')"
   ```
