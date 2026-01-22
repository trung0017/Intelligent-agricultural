#!/usr/bin/env python3
"""
Test script để kiểm tra tính năng phát hiện mâu thuẫn.

Sử dụng: python test_contradiction_detection.py
"""

import os
import sys
from pathlib import Path

# Thêm src vào path
sys.path.insert(0, str(Path(__file__).parent))

from src.models import AgriClaim
from src.agents.judge import (
    judge_claims,
    detect_contradictions_in_group,
    cluster_claims_by_semantic_similarity
)

def test_contradiction_detection():
    """Test phát hiện mâu thuẫn giữa 'giải nhất' và 'giải khuyến khích'"""
    
    print("=" * 60)
    print("🧪 TEST PHÁT HIỆN MÂU THUẪN")
    print("=" * 60)
    print()
    
    # Kiểm tra GOOGLE_API_KEY
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY chưa được thiết lập!")
        print("💡 Export: export GOOGLE_API_KEY='your-key-here'")
        return
    
    print("✅ GOOGLE_API_KEY đã được thiết lập")
    print()
    
    # Test case 1: Mâu thuẫn rõ ràng
    print("📋 Test Case 1: Giải nhất vs Giải khuyến khích")
    print("-" * 60)
    
    claim1 = AgriClaim(
        subject="Lúa ST25",
        predicate="Giải thưởng",
        object="Giải nhất cuộc thi Gạo Ngon Thế Giới",
        confidence=0.9
    )
    
    claim2 = AgriClaim(
        subject="Lúa ST25",
        predicate="Giải thưởng",
        object="Giải khuyến khích cuộc thi Gạo Ngon Thế Giới",
        confidence=0.9
    )
    
    print(f"Claim 1: {claim1.subject} - {claim1.predicate}: {claim1.object}")
    print(f"Claim 2: {claim2.subject} - {claim2.predicate}: {claim2.object}")
    print()
    
    print("🔄 Đang phân tích...")
    result = judge_claims(claim1, claim2, use_embedding=True, use_cache=True)
    
    print(f"Kết quả: {result['relation']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"From cache: {result.get('from_cache', False)}")
    print()
    
    if result['relation'] == 'CONTRADICTED':
        print("✅ THÀNH CÔNG: Phát hiện được mâu thuẫn!")
    else:
        print(f"⚠️ Kết quả: {result['relation']} (mong đợi: CONTRADICTED)")
    print()
    
    # Test case 2: Không mâu thuẫn (giống nhau)
    print("📋 Test Case 2: Hai claims giống nhau")
    print("-" * 60)
    
    claim3 = AgriClaim(
        subject="Lúa ST25",
        predicate="Năng suất",
        object="8.5 tấn/ha",
        confidence=0.9
    )
    
    claim4 = AgriClaim(
        subject="Lúa ST25",
        predicate="Năng suất",
        object="8.5 tấn/ha",
        confidence=0.85
    )
    
    result2 = judge_claims(claim3, claim4, use_embedding=True, use_cache=True)
    print(f"Claim 3: {claim3.object}")
    print(f"Claim 4: {claim4.object}")
    print(f"Kết quả: {result2['relation']}")
    print()
    
    # Test case 3: Detect trong group
    print("📋 Test Case 3: Phát hiện contradictions trong nhóm")
    print("-" * 60)
    
    claims_group = [
        claim1,  # Giải nhất
        claim2,  # Giải khuyến khích
        AgriClaim(
            subject="Lúa ST25",
            predicate="Giải thưởng",
            object="Giải nhất cuộc thi Gạo Ngon Thế Giới",
            confidence=0.95
        ),
    ]
    
    contradiction_info = detect_contradictions_in_group(
        claims_group,
        use_embedding=True,
        use_cache=True
    )
    
    print(f"Có contradictions: {contradiction_info['has_contradictions']}")
    print(f"Số cặp mâu thuẫn: {len(contradiction_info['contradiction_pairs'])}")
    
    if contradiction_info['contradiction_details']:
        print("\nChi tiết:")
        for detail in contradiction_info['contradiction_details']:
            print(f"  - {detail['claim1']}")
            print(f"    vs {detail['claim2']}")
            print(f"    Lý do: {detail['reasoning']}")
            print()
    
    # Test case 4: Semantic clustering
    print("📋 Test Case 4: Semantic clustering")
    print("-" * 60)
    
    test_claims = [
        AgriClaim(subject="A", predicate="P", object="Giải nhất", confidence=0.9),
        AgriClaim(subject="A", predicate="P", object="Giải nhất", confidence=0.9),
        AgriClaim(subject="A", predicate="P", object="Giải khuyến khích", confidence=0.9),
        AgriClaim(subject="A", predicate="P", object="Giải nhì", confidence=0.9),
    ]
    
    clusters = cluster_claims_by_semantic_similarity(test_claims, similarity_threshold=0.85)
    print(f"Số clusters: {len(clusters)}")
    for i, cluster in enumerate(clusters, 1):
        values = [c.object for c in cluster]
        print(f"  Cluster {i}: {values}")
    
    if len(clusters) >= 2:
        print("✅ THÀNH CÔNG: Tách được các giá trị khác nhau thành cluster riêng!")
    else:
        print("⚠️ Các giá trị khác nhau vẫn bị gộp chung")
    print()
    
    # Tổng kết
    print("=" * 60)
    print("📊 TỔNG KẾT")
    print("=" * 60)
    
    all_passed = (
        result['relation'] == 'CONTRADICTED' and
        result2['relation'] == 'SUPPORTED' and
        contradiction_info['has_contradictions'] and
        len(clusters) >= 2
    )
    
    if all_passed:
        print("✅ Tất cả test cases đều PASS!")
    else:
        print("⚠️ Một số test cases chưa đạt kỳ vọng")
        print("💡 Kiểm tra lại GOOGLE_API_KEY và embedding model")


if __name__ == "__main__":
    test_contradiction_detection()
