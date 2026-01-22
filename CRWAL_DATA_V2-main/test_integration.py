#!/usr/bin/env python3
"""
Script test tích hợp giữa CRWAL_DATA_V2-main và agri-agent-system

Sử dụng: python test_integration.py
"""

import sys
from pathlib import Path

print("=" * 60)
print("🧪 TEST TÍCH HỢP AGRI-AGENT VÀO WIKINONGSAN")
print("=" * 60)
print()

# Test 1: Kiểm tra đường dẫn
print("📁 Test 1: Kiểm tra đường dẫn")
print("-" * 60)

AGRI_AGENT_PATH = Path(__file__).parent.parent / "agri-agent-system"
print(f"Đường dẫn agri-agent-system: {AGRI_AGENT_PATH}")
print(f"Tồn tại: {'✅ Có' if AGRI_AGENT_PATH.exists() else '❌ Không'}")
print()

# Test 2: Kiểm tra sys.path
print("🔍 Test 2: Kiểm tra sys.path")
print("-" * 60)

if str(AGRI_AGENT_PATH) not in sys.path:
    sys.path.insert(0, str(AGRI_AGENT_PATH))
    print(f"✅ Đã thêm vào sys.path: {AGRI_AGENT_PATH}")
else:
    print(f"✅ Đã có trong sys.path: {AGRI_AGENT_PATH}")
print()

# Test 3: Kiểm tra import
print("📦 Test 3: Kiểm tra import modules")
print("-" * 60)

try:
    from src.models import AgriClaim
    print("✅ Import AgriClaim thành công")
except ImportError as e:
    print(f"❌ Import AgriClaim thất bại: {e}")
    sys.exit(1)

try:
    from src.agents.extractor import extract_claims_from_text
    print("✅ Import extract_claims_from_text thành công")
except ImportError as e:
    print(f"❌ Import extract_claims_from_text thất bại: {e}")
    sys.exit(1)

try:
    from src.agents.resolver import group_and_resolve_claims, ResolvedClaim
    print("✅ Import group_and_resolve_claims thành công")
except ImportError as e:
    print(f"❌ Import group_and_resolve_claims thất bại: {e}")
    sys.exit(1)
print()

# Test 4: Kiểm tra GOOGLE_API_KEY
print("🔑 Test 4: Kiểm tra GOOGLE_API_KEY")
print("-" * 60)

import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    print(f"✅ GOOGLE_API_KEY đã được thiết lập: {api_key[:10]}...")
else:
    print("⚠️ GOOGLE_API_KEY chưa được thiết lập")
    print("   💡 Tạo file .env và thêm: GOOGLE_API_KEY=your-key-here")
print()

# Test 5: Test extract claims (nếu có API key)
print("🤖 Test 5: Test extract claims từ text mẫu")
print("-" * 60)

if api_key:
    test_text = """
    Lúa ST25 là giống lúa nổi tiếng của Việt Nam.
    Năng suất trung bình đạt 8.5 tấn/ha trong vụ Đông Xuân.
    Thời gian sinh trưởng khoảng 95-100 ngày.
    Giống lúa này có khả năng chịu mặn tốt, phù hợp với vùng ven biển ĐBSCL.
    """
    
    try:
        claims = extract_claims_from_text(test_text)
        print(f"✅ Trích xuất thành công {len(claims)} claims")
        
        if claims:
            print("\n📋 Claims trích xuất:")
            for i, claim in enumerate(claims[:3], 1):
                print(f"  {i}. {claim.subject} - {claim.predicate}: {claim.object}")
                print(f"     Context: {claim.context}")
                print(f"     Confidence: {claim.confidence:.2f}")
                print()
    except Exception as e:
        print(f"❌ Lỗi khi extract claims: {e}")
        print("   💡 Kiểm tra GOOGLE_API_KEY có đúng không")
else:
    print("⏭️ Bỏ qua test extract (chưa có GOOGLE_API_KEY)")
print()

# Test 6: Test validator module
print("✅ Test 6: Kiểm tra validator module")
print("-" * 60)

try:
    from validator import (
        AGRI_AGENT_AVAILABLE,
        IMPORT_ERROR,
        validate_wiki_article,
        get_validation_summary
    )
    
    if AGRI_AGENT_AVAILABLE:
        print("✅ Agri-Agent khả dụng")
        print("✅ Validator module hoạt động tốt")
    else:
        print(f"❌ Agri-Agent không khả dụng: {IMPORT_ERROR}")
except ImportError as e:
    print(f"❌ Không thể import validator: {e}")
print()

# Test 7: Test với bài viết thật (nếu có)
print("📄 Test 7: Test với bài viết wiki thật")
print("-" * 60)

pages_dir = Path("pages")
if pages_dir.exists():
    md_files = list(pages_dir.glob("*.md"))
    if md_files:
        test_file = md_files[0]
        print(f"📄 Tìm thấy bài viết: {test_file.name}")
        
        if api_key and AGRI_AGENT_AVAILABLE:
            try:
                from validator import validate_wiki_article, get_validation_summary
                result = validate_wiki_article(str(test_file))
                
                if result["success"]:
                    print("✅ Validation thành công!")
                    print(f"   - Claims: {len(result['claims'])}")
                    print(f"   - Resolved: {len(result['resolved_claims'])}")
                    print(f"   - Score: {result['validation_score']:.2%}")
                    print("\n📊 Tóm tắt:")
                    print(get_validation_summary(result))
                else:
                    print("❌ Validation thất bại")
                    print(f"   Errors: {result['errors']}")
            except Exception as e:
                print(f"❌ Lỗi khi validate: {e}")
        else:
            print("⏭️ Bỏ qua (chưa có GOOGLE_API_KEY hoặc Agri-Agent không khả dụng)")
    else:
        print("⚠️ Không tìm thấy file markdown nào trong pages/")
else:
    print("⚠️ Thư mục pages/ không tồn tại")
print()

# Tổng kết
print("=" * 60)
print("📊 TỔNG KẾT")
print("=" * 60)

all_ok = True
if not AGRI_AGENT_PATH.exists():
    print("❌ agri-agent-system không tồn tại")
    all_ok = False

try:
    from src.models import AgriClaim
except ImportError:
    print("❌ Không thể import từ agri-agent-system")
    all_ok = False

if not api_key:
    print("⚠️ GOOGLE_API_KEY chưa được thiết lập (cần để sử dụng validation)")

if all_ok:
    print("✅ Tất cả kiểm tra cơ bản đều OK!")
    print("💡 Bạn có thể sử dụng tính năng validation trong Admin Dashboard")
else:
    print("❌ Có một số vấn đề cần khắc phục")
    print("💡 Xem file HOW_IT_WORKS.md để biết cách sửa")

print()
