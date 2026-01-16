# 🚀 Hướng dẫn cài đặt WikiNongSan

> **Hướng dẫn chi tiết từng bước để cài đặt và chạy WikiNongSan trên máy tính của bạn**

## 📋 Yêu cầu hệ thống

### Phần cứng tối thiểu
- **RAM**: 8GB (khuyến nghị 16GB cho AI)
- **CPU**: Intel i5 hoặc AMD Ryzen 5 trở lên
- **Ổ cứng**: 10GB dung lượng trống
- **Kết nối**: Internet ổn định

### Hệ điều hành hỗ trợ
- ✅ **Windows 10/11** (64-bit)
- ✅ **macOS 10.15+**
- ✅ **Ubuntu 20.04+**
- ✅ **CentOS 8+**

## 🛠️ Bước 1: Cài đặt Python

### Windows
1. **Tải Python 3.8+** từ https://python.org/downloads/
2. **Chạy installer**, tích chọn "Add Python to PATH"
3. **Kiểm tra cài đặt**:
   ```cmd
   python --version
   pip --version
   ```

### macOS
```bash
# Sử dụng Homebrew (khuyến nghị)
brew install python@3.9

# Hoặc tải từ python.org
```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### CentOS/RHEL
```bash
sudo yum install python3 python3-pip
```

## 🤖 Bước 2: Cài đặt Ollama AI

### Windows
1. **Tải Ollama** từ https://ollama.ai/download
2. **Chạy installer** và làm theo hướng dẫn
3. **Khởi động Ollama**:
   ```cmd
   ollama serve --host 127.0.0.1:11500
   ```

### macOS
```bash
# Tải và cài đặt từ ollama.ai
curl -fsSL https://ollama.ai/install.sh | sh

# Khởi động
ollama serve --host 127.0.0.1:11500
```

### Linux
```bash
# Cài đặt Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Khởi động service
ollama serve --host 127.0.0.1:11500
```

### Tải mô hình AI
```bash
# Tải mô hình Qwen2.5:7B (khuyến nghị cho tiếng Việt)
ollama pull qwen2.5:7b

# Kiểm tra mô hình đã tải
ollama list
```

## 📦 Bước 3: Tải và cài đặt WikiNongSan

### Tải source code
```bash
# Option 1: Clone từ Git (nếu có)
git clone https://github.com/phuctoichoi/CRWAL_DATA_V2.git
cd wikinongsang

# Option 2: Tải ZIP và giải nén
# Tải file ZIP → Giải nén → Mở terminal trong thư mục
```

### Tạo môi trường ảo (khuyến nghị)
```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt virtual environment
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

### Cài đặt dependencies
```bash
# Cài đặt tất cả thư viện cần thiết
pip install -r requirements.txt

# Nếu gặp lỗi, thử upgrade pip trước
pip install --upgrade pip
pip install -r requirements.txt
```

## ⚙️ Bước 4: Cấu hình hệ thống

### Cấu hình Ollama
```bash
# Thiết lập biến môi trường (Windows)
set OLLAMA_HOST=127.0.0.1:11500

# macOS/Linux
export OLLAMA_HOST=127.0.0.1:11500
```

### Tạo thư mục cần thiết
Hệ thống sẽ tự động tạo, nhưng bạn có thể tạo trước:
```bash
mkdir pages raw_content cleaned_content static/uploads
```

### Kiểm tra cấu hình
```bash
# Test kết nối Ollama
python -c "
import requests
try:
    response = requests.get('http://127.0.0.1:11500/api/tags')
    print('✅ Ollama hoạt động:', response.status_code == 200)
except:
    print('❌ Ollama chưa chạy')
"
```

## 🚀 Bước 5: Khởi động hệ thống

### Khởi động Ollama (Terminal 1)
```bash
# Mở terminal đầu tiên
ollama serve --host 127.0.0.1:11500
```

### Khởi động WikiNongSan (Terminal 2)
```bash
# Mở terminal thứ hai, vào thư mục dự án
cd wikinongsang

# Kích hoạt virtual environment (nếu dùng)
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Chạy website
python app.py
```

### Sử dụng file batch (Windows)
```cmd
# Khởi động Ollama
start_ollama_custom.bat

# Khởi động website
start_wiki.bat
```

## 🌐 Bước 6: Truy cập và sử dụng

### Truy cập website
1. **Mở trình duyệt** (Chrome, Firefox, Edge...)
2. **Vào địa chỉ**: http://localhost:8000
3. **Trang chủ** sẽ hiển thị danh sách bài viết

### Đăng nhập Admin
1. **Click "Đăng nhập"** ở góc phải header
2. **Nhập thông tin**:
   - Username: `admin`
   - Password: `123`
3. **Truy cập Dashboard** để quản lý nội dung

### Sử dụng Crawler
1. **Vào Admin Dashboard** → **Crawler & AI**
2. **Nhập chủ đề** bài viết
3. **Thêm 1-5 URLs** từ các trang tin tức
4. **Click "Bắt đầu thu thập"**
5. **Theo dõi tiến trình** real-time
6. **Sử dụng "Text Cleaner"** để AI xử lý

## 🔧 Khắc phục sự cố

### Lỗi thường gặp

#### ❌ "ModuleNotFoundError"
```bash
# Cài lại dependencies
pip install -r requirements.txt

# Hoặc cài từng package
pip install fastapi uvicorn requests beautifulsoup4 playwright markdown
```

#### ❌ "Ollama connection failed"
```bash
# Kiểm tra Ollama có chạy không
curl http://127.0.0.1:11500/api/tags

# Khởi động lại Ollama
ollama serve --host 127.0.0.1:11500
```

#### ❌ "Port 8000 already in use"
```bash
# Thay đổi port trong app.py (dòng cuối)
uvicorn.run(app, host="127.0.0.1", port=8001)
```

#### ❌ "Permission denied"
```bash
# Linux/macOS: Cấp quyền thực thi
chmod +x *.bat
sudo chown -R $USER:$USER .
```

### Kiểm tra log lỗi
```bash
# Chạy với verbose để xem lỗi chi tiết
python app.py --log-level debug
```

## 🔒 Bảo mật

### Thay đổi mật khẩu admin
1. **Mở file** `app.py`
2. **Tìm dòng** `ADMIN_PASSWORD = "123"`
3. **Thay đổi** thành mật khẩu mạnh
4. **Khởi động lại** server

### Cấu hình firewall
```bash
# Chỉ cho phép truy cập local
# Không mở port 8000 ra internet nếu không cần thiết
```

## 📈 Tối ưu hiệu suất

### Tăng tốc AI
```bash
# Sử dụng GPU (nếu có)
ollama serve --gpu

# Tăng RAM cho Ollama
export OLLAMA_MAX_LOADED_MODELS=2
```

### Tối ưu database
- Định kỳ dọn dẹp file raw_content cũ
- Backup thư mục pages thường xuyên

## 🆘 Hỗ trợ

### Tự khắc phục
1. **Đọc log lỗi** trong terminal
2. **Kiểm tra requirements** đã cài đủ chưa
3. **Restart** cả Ollama và WikiNongSan
4. **Kiểm tra port** có bị chiếm không

### Liên hệ hỗ trợ
- **📧 Email**: support@wikinongsang.com
- **💬 Community**: [Discord/Telegram link]
- **📖 Documentation**: [Wiki link]

## 🎯 Bước tiếp theo

Sau khi cài đặt thành công:

1. **📚 Tạo nội dung đầu tiên** bằng Crawler
2. **🎨 Tùy chỉnh giao diện** (CSS trong static/)
3. **🔧 Cấu hình nâng cao** (AI prompts, themes...)
4. **📊 Monitoring** và backup định kỳ

---

<div align="center">

**🎉 Chúc mừng! Bạn đã cài đặt thành công WikiNongSan! 🎉**



</div>

