from __future__ import annotations

"""
Resolver agent: hợp nhất các AgriClaim từ nhiều nguồn bằng thuật toán Weighted Voting.

Theo PROMPTS.md:
1. Clustering: Gom nhóm các giá trị xấp xỉ nhau (VD: 8.0 tấn, 8.1 tấn là 1 nhóm).
2. Scoring: Điểm nhóm = Tổng (Trust Score của nguồn * Hệ số thời gian).
   - Hệ số thời gian: Năm hiện tại (1.2), cũ hơn (1.0).
3. Decision: Chọn nhóm điểm cao nhất làm "Gold Standard".
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple
import math
import re

from src.models import AgriClaim
from src.tools.filter import calculate_trust_score


CURRENT_YEAR_BOOST = 1.2
OLDER_YEAR_FACTOR = 1.0


@dataclass
class ResolvedClaim:
    """
    Kết quả sau khi hợp nhất các claim.
    """

    gold_claim: AgriClaim
    support_urls: List[str]
    total_score: float
    cluster_values: List[str]
    has_contradictions: bool = False
    contradiction_details: List[Dict] = None
    
    def __post_init__(self):
        if self.contradiction_details is None:
            self.contradiction_details = []


def _extract_year_from_context(context: Optional[str]) -> Optional[int]:
    """
    Tìm năm (4 chữ số) trong context, ưu tiên nằm trong khoảng 1900-2100.
    """
    if not context:
        return None
    matches = re.findall(r"(19|20)\d{2}", context)
    if not matches:
        return None
    try:
        # Lấy năm đầu tiên hợp lệ
        year_str = matches[0]
        year = int(year_str if isinstance(year_str, str) else "".join(year_str))
        if 1900 <= year <= 2100:
            return year
    except ValueError:
        return None
    return None


def _time_weight_for_claim(claim: AgriClaim) -> float:
    """
    Hệ số thời gian:
    - Nếu năm trong context == năm hiện tại -> 1.2
    - Ngược lại -> 1.0
    """
    year = _extract_year_from_context(claim.context)
    if not year:
        return OLDER_YEAR_FACTOR

    current_year = datetime.now().year
    if year == current_year:
        return CURRENT_YEAR_BOOST
    return OLDER_YEAR_FACTOR


def _parse_numeric_value(value: str) -> Optional[float]:
    """
    Cố gắng trích xuất giá trị số đại diện từ chuỗi (VD: '8.5 tấn/ha', '95-100 ngày').
    Ưu tiên:
    - Nếu có khoảng a-b -> lấy trung bình (a+b)/2
    - Nếu chỉ có một số -> lấy số đó
    """
    if not value:
        return None

    # Tìm tất cả số (hỗ trợ số thập phân với dấu . hoặc ,)
    numbers = re.findall(r"\d+(?:[.,]\d+)?", value)
    if not numbers:
        return None

    floats = []
    for n in numbers:
        try:
            floats.append(float(n.replace(",", ".")))
        except ValueError:
            continue

    if not floats:
        return None

    if len(floats) == 1:
        return floats[0]

    # Nếu có nhiều số, coi như khoảng và lấy trung bình
    return sum(floats) / len(floats)


def _cluster_text_values_simple(claims: List[AgriClaim]) -> List[List[AgriClaim]]:
    """
    Cluster text values đơn giản bằng exact matching (fallback).
    """
    if not claims:
        return []
    
    clusters: List[List[AgriClaim]] = []
    for claim in claims:
        claim_value = (claim.object or "").strip().lower()
        matched = False
        
        for cluster in clusters:
            cluster_value = (cluster[0].object or "").strip().lower()
            if claim_value == cluster_value:
                cluster.append(claim)
                matched = True
                break
        
        if not matched:
            clusters.append([claim])
    
    return clusters


def _cluster_numeric_values(values: List[Tuple[AgriClaim, float]]) -> List[List[Tuple[AgriClaim, float]]]:
    """
    Gom nhóm các claim có giá trị số xấp xỉ nhau.

    values: List[(claim, numeric_value)]
    Chiến lược đơn giản:
    - Sắp xếp theo numeric_value
    - Duyệt từ trái sang phải, nếu chênh lệch tương đối <= 5% với tâm cụm hiện tại thì vào cùng cụm,
      ngược lại tạo cụm mới.
    """
    if not values:
        return []

    # Sắp xếp theo numeric_value
    values_sorted = sorted(values, key=lambda x: x[1])

    clusters: List[List[Tuple[AgriClaim, float]]] = []
    current_cluster: List[Tuple[AgriClaim, float]] = [values_sorted[0]]
    cluster_center = values_sorted[0][1]

    for claim, num in values_sorted[1:]:
        # chênh lệch tương đối so với tâm cụm
        if cluster_center == 0:
            rel_diff = abs(num - cluster_center)
        else:
            rel_diff = abs(num - cluster_center) / abs(cluster_center)

        if rel_diff <= 0.05:  # 5%
            current_cluster.append((claim, num))
            # cập nhật tâm cụm là trung bình
            cluster_center = sum(v for _, v in current_cluster) / len(current_cluster)
        else:
            clusters.append(current_cluster)
            current_cluster = [(claim, num)]
            cluster_center = num

    clusters.append(current_cluster)
    return clusters


def resolve_claims_for_group(claims: Iterable[AgriClaim]) -> Optional[ResolvedClaim]:
    """
    Nhận vào các claim đã cùng (subject, predicate, context cấu trúc),
    thực hiện weighted voting theo giá trị object (numeric nếu có).
    """
    claim_list = list(claims)
    if not claim_list:
        return None

    # Tách các claim có giá trị số (để cluster)
    numeric_items: List[Tuple[AgriClaim, float]] = []
    non_numeric_items: List[AgriClaim] = []

    for c in claim_list:
        if c.object is None:
            non_numeric_items.append(c)
            continue
        num = _parse_numeric_value(c.object)
        if num is None:
            non_numeric_items.append(c)
        else:
            numeric_items.append((c, num))

    clusters_scores: List[Tuple[float, List[AgriClaim]]] = []

    # 1) Xử lý cụm numeric
    if numeric_items:
        clusters = _cluster_numeric_values(numeric_items)
        for cluster in clusters:
            score = 0.0
            cluster_claims: List[AgriClaim] = []
            for claim, _val in cluster:
                trust = calculate_trust_score(claim.source_url or "")
                time_w = _time_weight_for_claim(claim)
                score += trust * time_w
                cluster_claims.append(claim)
            clusters_scores.append((score, cluster_claims))

    # 2) Các claim non-numeric: cluster theo semantic similarity
    if non_numeric_items:
        # Sử dụng semantic clustering từ judge module
        try:
            from src.agents.judge import cluster_claims_by_semantic_similarity
            text_clusters = cluster_claims_by_semantic_similarity(
                non_numeric_items,
                similarity_threshold=0.85
            )
        except ImportError:
            # Fallback: cluster đơn giản theo giá trị text
            text_clusters = _cluster_text_values_simple(non_numeric_items)
        
        for cluster in text_clusters:
            score = 0.0
            for claim in cluster:
                trust = calculate_trust_score(claim.source_url or "")
                time_w = _time_weight_for_claim(claim)
                score += trust * time_w
            clusters_scores.append((score, cluster))

    if not clusters_scores:
        return None

    # 3) Chọn cụm có tổng điểm cao nhất
    clusters_scores.sort(key=lambda x: x[0], reverse=True)
    best_score, best_cluster_claims = clusters_scores[0]

    # Chọn gold_claim:
    # - Nếu cluster numeric: lấy claim có numeric_value gần trung bình nhất
    # - Nếu non-numeric: lấy claim có confidence cao nhất (tie-break: trust score)
    if best_cluster_claims and _parse_numeric_value(best_cluster_claims[0].object or "") is not None:
        # numeric cluster
        numeric_pairs = [
            (c, _parse_numeric_value(c.object or ""))
            for c in best_cluster_claims
            if _parse_numeric_value(c.object or "") is not None
        ]
        avg_val = sum(v for _, v in numeric_pairs) / len(numeric_pairs)

        def distance_to_avg(item: Tuple[AgriClaim, float]) -> float:
            return abs(item[1] - avg_val)

        gold_claim = min(numeric_pairs, key=distance_to_avg)[0]
    else:
        # non-numeric cluster
        def scoring(c: AgriClaim) -> float:
            trust = calculate_trust_score(c.source_url or "")
            return c.confidence + 0.1 * trust

        gold_claim = max(best_cluster_claims, key=scoring)

    support_urls = list(
        {c.source_url for c in best_cluster_claims if c.source_url}
    )
    cluster_values = [
        c.object for c in best_cluster_claims if c.object is not None
    ]
    
    # Phát hiện contradictions trong cluster
    has_contradictions = False
    contradiction_details = []
    
    if len(best_cluster_claims) > 1:
        try:
            from src.agents.judge import detect_contradictions_in_group
            
            contradiction_info = detect_contradictions_in_group(
                best_cluster_claims,
                use_embedding=True,
                use_cache=True
            )
            
            has_contradictions = contradiction_info["has_contradictions"]
            contradiction_details = contradiction_info["contradiction_details"]
        except ImportError:
            # Fallback: kiểm tra đơn giản
            unique_values = set(
                (c.object or "").strip().lower() 
                for c in best_cluster_claims 
                if c.object
            )
            if len(unique_values) > 1:
                has_contradictions = True
                contradiction_details = [{
                    "reasoning": f"Phát hiện {len(unique_values)} giá trị khác nhau: {', '.join(list(unique_values)[:3])}"
                }]

    return ResolvedClaim(
        gold_claim=gold_claim,
        support_urls=support_urls,
        total_score=best_score,
        cluster_values=cluster_values,
        has_contradictions=has_contradictions,
        contradiction_details=contradiction_details,
    )


def group_and_resolve_claims(claims: Iterable[AgriClaim]) -> List[ResolvedClaim]:
    """
    Nhận vào danh sách claim (từ nhiều URL), group và resolve.

    Group key đơn giản:
    - subject
    - predicate
    """
    from collections import defaultdict

    groups: Dict[Tuple[str, str], List[AgriClaim]] = defaultdict(list)
    for c in claims:
        key = (c.subject.strip().lower(), c.predicate.strip().lower())
        groups[key].append(c)

    results: List[ResolvedClaim] = []
    for _key, group_claims in groups.items():
        resolved = resolve_claims_for_group(group_claims)
        if resolved:
            results.append(resolved)

    return results


__all__ = [
    "ResolvedClaim",
    "resolve_claims_for_group",
    "group_and_resolve_claims",
]

