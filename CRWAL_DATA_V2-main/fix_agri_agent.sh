#!/bin/bash

# Script sửa lỗi "Agri-Agent không khả dụng"
# Chạy script này trong thư mục CRWAL_DATA_V2-main

echo "🔧 Đang sửa lỗi Agri-Agent..."
echo ""

# Kiểm tra venv
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment chưa được tạo!"
    echo "💡 Chạy: python3 -m venv venv"
    exit 1
fi

# Kích hoạt venv
echo "📦 Kích hoạt virtual environment..."
source venv/bin/activate

# Nâng cấp pip
echo "⬆️  Nâng cấp pip..."
pip install --upgrade pip --quiet

# Cài đặt dependencies
echo "📥 Cài đặt dependencies của Agri-Agent..."
pip install langgraph>=0.2.0 langchain>=0.3.0 langchain-google-genai>=2.0.0 pydantic>=2.0.0 trafilatura>=1.6.0 ddgs>=1.0.0 charset-normalizer>=3.0.0 chromadb>=0.5.0

# Kiểm tra cài đặt
echo ""
echo "✅ Kiểm tra cài đặt..."
python -c "from langchain_google_genai import ChatGoogleGenerativeAI; print('✅ langchain_google_genai: OK')" 2>/dev/null || echo "❌ langchain_google_genai: Lỗi"

python -c "from src.models import AgriClaim" 2>/dev/null && echo "✅ Agri-Agent models: OK" || echo "⚠️  Agri-Agent models: Cần kiểm tra đường dẫn"

# Kiểm tra GOOGLE_API_KEY
echo ""
echo "🔑 Kiểm tra GOOGLE_API_KEY..."
if [ -f ".env" ]; then
    if grep -q "GOOGLE_API_KEY" .env && ! grep -q "GOOGLE_API_KEY=$" .env; then
        echo "✅ GOOGLE_API_KEY đã được thiết lập trong .env"
    else
        echo "⚠️  GOOGLE_API_KEY chưa được thiết lập trong .env"
        echo "💡 Thêm vào .env: GOOGLE_API_KEY=your-api-key-here"
    fi
else
    echo "⚠️  File .env chưa tồn tại"
    echo "💡 Tạo file .env và thêm: GOOGLE_API_KEY=your-api-key-here"
fi

echo ""
echo "🎉 Hoàn tất!"
echo ""
echo "📝 Tiếp theo:"
echo "   1. Đảm bảo GOOGLE_API_KEY đã được thiết lập trong .env"
echo "   2. Khởi động lại server: python app.py"
echo "   3. Truy cập: http://localhost:8000/admin/dashboard"
