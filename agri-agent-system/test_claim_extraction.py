#!/usr/bin/env python3
"""
Test script để so sánh số lượng claims trước và sau khi cải thiện.

Chạy script này để xem số lượng claims được trích xuất từ một bài viết mẫu.
"""

import os
import sys
from pathlib import Path

# Thêm thư mục gốc vào path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.extractor import extract_claims_from_text

# Bài viết mẫu về Lúa ST25
SAMPLE_TEXT = """
# Lúa ST25 - Giống lúa nổi tiếng Việt Nam

Lúa ST25 là giống lúa nổi tiếng của Việt Nam, được phát triển bởi kỹ sư Hồ Quang Cua 
và cộng sự. Giống lúa này đã đạt giải nhất cuộc thi Gạo Ngon Thế Giới năm 2019, 
đánh dấu một bước tiến quan trọng của nông nghiệp Việt Nam.

## Đặc điểm năng suất

Năng suất trung bình của lúa ST25 đạt 8.5 tấn/ha trong vụ Đông Xuân tại vùng ĐBSCL. 
Trong điều kiện canh tác tốt, năng suất có thể đạt tới 9.0-9.5 tấn/ha. 
Thời gian sinh trưởng của giống lúa này khoảng 95-100 ngày, phù hợp với 
chu kỳ canh tác vùng ĐBSCL.

## Đặc điểm hình thái và chất lượng

Hạt gạo ST25 có đặc điểm dài, dẻo vừa, màu trắng đều và bóng. Khi nấu, 
gạo tỏa hương thơm đặc trưng, mùi thơm tự nhiên rất hấp dẫn. Gạo sau khi nấu 
có độ dẻo vừa phải, không quá dẻo cũng không quá khô.

## Khả năng chịu đựng

Giống lúa ST25 có khả năng chịu mặn tốt, chịu được độ mặn 4-6‰, phù hợp với 
vùng ven biển ĐBSCL. Ngoài ra, giống lúa này cũng có khả năng chịu hạn tốt, 
phù hợp với điều kiện khí hậu khô hạn.

## Điều kiện canh tác

Lúa ST25 thích hợp trồng ở vùng ven biển ĐBSCL, đặc biệt là các tỉnh Sóc Trăng, 
Bạc Liêu, Cà Mau. Giống lúa này phù hợp với vụ Đông Xuân và vụ Hè Thu. 
Mật độ gieo trồng khuyến nghị là 120-150 kg/ha.

## Giải thưởng và thành tích

Ngoài giải nhất cuộc thi Gạo Ngon Thế Giới năm 2019, lúa ST25 còn đạt nhiều 
giải thưởng khác trong nước và quốc tế. Giống lúa này đã được công nhận là 
một trong những giống lúa chất lượng cao nhất thế giới.

## So sánh với giống khác

So với giống lúa ST24, ST25 có năng suất cao hơn khoảng 10-15% và chất lượng 
gạo tốt hơn. Hàm lượng protein trong gạo ST25 cũng cao hơn so với các giống 
lúa thông thường, đạt trên 7% protein.
"""


def main():
    """Test trích xuất claims."""
    print("=" * 70)
    print("🧪 TEST TRÍCH XUẤT CLAIMS - So sánh trước và sau cải thiện")
    print("=" * 70)
    print()
    
    # Kiểm tra API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Lỗi: GOOGLE_API_KEY chưa được thiết lập!")
        print("   Hãy thiết lập biến môi trường GOOGLE_API_KEY trước khi chạy.")
        return
    
    print("📝 Bài viết mẫu:")
    print(f"   - Độ dài: {len(SAMPLE_TEXT)} ký tự")
    print(f"   - Số từ: ~{len(SAMPLE_TEXT.split())} từ")
    print()
    
    print("🔄 Đang trích xuất claims...")
    print("   (Có thể mất vài giây)")
    print()
    
    try:
        # Trích xuất claims
        claims = extract_claims_from_text(SAMPLE_TEXT, use_chunking=True)
        
        print("=" * 70)
        print(f"✅ KẾT QUẢ: Trích xuất được {len(claims)} claims")
        print("=" * 70)
        print()
        
        if claims:
            print("📋 Danh sách claims:")
            print()
            for i, claim in enumerate(claims, 1):
                print(f"{i}. Subject: {claim.subject}")
                print(f"   Predicate: {claim.predicate}")
                print(f"   Object: {claim.object or '(null)'}")
                if claim.context:
                    print(f"   Context: {claim.context}")
                print(f"   Confidence: {claim.confidence:.2f}")
                print()
            
            # Thống kê
            print("=" * 70)
            print("📊 THỐNG KÊ:")
            print("=" * 70)
            
            # Đếm theo predicate
            predicates = {}
            for claim in claims:
                pred = claim.predicate
                predicates[pred] = predicates.get(pred, 0) + 1
            
            print("\nSố lượng claims theo loại (predicate):")
            for pred, count in sorted(predicates.items(), key=lambda x: -x[1]):
                print(f"   - {pred}: {count} claims")
            
            # Đếm claims có object
            claims_with_object = sum(1 for c in claims if c.object)
            print(f"\nClaims có object (số liệu/mô tả): {claims_with_object}/{len(claims)}")
            
            # Confidence trung bình
            avg_confidence = sum(c.confidence for c in claims) / len(claims)
            print(f"Confidence trung bình: {avg_confidence:.2f}")
            
            print()
            print("=" * 70)
            print("💡 KỲ VỌNG:")
            print("=" * 70)
            print("   - Trước cải thiện: 5-7 claims")
            print("   - Sau cải thiện: 10-15+ claims")
            print(f"   - Kết quả hiện tại: {len(claims)} claims")
            
            if len(claims) >= 10:
                print("   ✅ Đạt mục tiêu!")
            else:
                print("   ⚠️  Chưa đạt mục tiêu, có thể cần điều chỉnh thêm.")
        else:
            print("❌ Không trích xuất được claims nào!")
            print("   Có thể do:")
            print("   - API key không hợp lệ")
            print("   - Lỗi kết nối API")
            print("   - Văn bản không phù hợp")
    
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
