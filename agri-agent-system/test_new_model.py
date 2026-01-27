#!/usr/bin/env python3
"""
Script test model mới (gemini-2.5-flash-lite) để tránh rate limit.
"""

import os
import sys
from pathlib import Path

# Thêm thư mục gốc vào path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.agents.extractor import _get_gemini_client, extract_claims_from_text
from src.agents.judge import _get_gemini_client as get_judge_client

def test_model():
    """Test model mới."""
    print("=" * 70)
    print("🧪 TEST MODEL MỚI: gemini-2.5-flash-lite")
    print("=" * 70)
    print()
    
    # Kiểm tra API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY chưa được thiết lập!")
        return
    
    print("✅ GOOGLE_API_KEY đã được thiết lập")
    print()
    
    # Test Extractor model
    print("📝 Test Extractor Model:")
    try:
        extractor_client = _get_gemini_client()
        print(f"   Model: {extractor_client.model_name}")
        print(f"   Temperature: {extractor_client.temperature}")
        print("   ✅ Extractor model OK")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        return
    
    print()
    
    # Test Judge model
    print("⚖️  Test Judge Model:")
    try:
        judge_client = get_judge_client()
        print(f"   Model: {judge_client.model_name}")
        print(f"   Temperature: {judge_client.temperature}")
        print("   ✅ Judge model OK")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        return
    
    print()
    
    # Test extraction với text ngắn
    print("🔄 Test Extraction (với text ngắn):")
    test_text = """
    Lúa ST25 là giống lúa nổi tiếng của Việt Nam.
    Năng suất đạt 8.5 tấn/ha trong vụ Đông Xuân.
    Giống lúa này đã đạt giải nhất cuộc thi Gạo Ngon Thế Giới năm 2019.
    """
    
    try:
        print("   Đang trích xuất claims...")
        claims = extract_claims_from_text(test_text, use_chunking=False)
        print(f"   ✅ Trích xuất được {len(claims)} claims")
        
        if claims:
            print()
            print("   Claims trích xuất:")
            for i, claim in enumerate(claims[:3], 1):  # Chỉ hiển thị 3 claims đầu
                print(f"   {i}. {claim.subject} - {claim.predicate}: {claim.object}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("=" * 70)
    print("✅ TEST HOÀN TẤT!")
    print("=" * 70)
    print()
    print("💡 Model mới: gemini-2.5-flash-lite")
    print("   - Còn trống: 0/10 RPM, 0/20 RPD")
    print("   - Có thể test thêm mà không lo vượt limit")
    print()
    print("⚠️  Lưu ý:")
    print("   - Vẫn cần tuân thủ delay 15 giây giữa requests")
    print("   - Chỉ test 1-2 queries để tránh vượt limit")
    print("   - Monitor Google AI Studio để theo dõi usage")


if __name__ == "__main__":
    test_model()
