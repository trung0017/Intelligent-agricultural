"""
Module tích hợp Agri-Agent để kiểm tra và validate bài viết wiki.

Chức năng:
- Đọc bài viết wiki từ thư mục pages/
- Trích xuất claims bằng Agri-Agent Extractor
- Validate claims bằng Resolver (Weighted Voting)
- Tạo báo cáo validation với độ tin cậy
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

# Thêm đường dẫn đến agri-agent-system vào sys.path
AGRI_AGENT_PATH = Path(__file__).parent.parent / "agri-agent-system"
if str(AGRI_AGENT_PATH) not in sys.path:
    sys.path.insert(0, str(AGRI_AGENT_PATH))

try:
    from src.agents.extractor import extract_claims_from_text, extract_claims_from_url
    from src.agents.resolver import group_and_resolve_claims, ResolvedClaim
    from src.agents.judge import judge_claims
    from src.models import AgriClaim
    from src.workflows.main import run_agri_workflow
    AGRI_AGENT_AVAILABLE = True
    IMPORT_ERROR = None
except ImportError as e:
    AGRI_AGENT_AVAILABLE = False
    IMPORT_ERROR = str(e)


def extract_text_from_markdown(markdown_content: str) -> str:
    """
    Trích xuất text thuần từ markdown, loại bỏ:
    - Headers (#)
    - Links [text](url)
    - Images
    - Code blocks
    - Metadata (phần sau ---)
    """
    text = markdown_content
    
    # Loại bỏ metadata (phần sau dòng ---)
    if "---" in text:
        parts = text.split("---")
        text = parts[0]  # Chỉ lấy phần trước ---
    
    # Loại bỏ code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    
    # Loại bỏ links nhưng giữ text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Loại bỏ headers (#)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Loại bỏ bold/italic markers
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    
    # Loại bỏ list markers
    text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Loại bỏ blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Loại bỏ nhiều khoảng trắng
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    
    return text.strip()


def validate_wiki_article(article_path: str, use_web_validation: bool = True) -> Dict[str, Any]:
    """
    Validate một bài viết wiki bằng Agri-Agent.
    
    Parameters
    ----------
    article_path: str
        Đường dẫn đến file markdown bài viết
        
    Returns
    -------
    Dict chứa:
    - success: bool
    - claims: List[AgriClaim] - các claims được trích xuất
    - resolved_claims: List[ResolvedClaim] - claims đã được validate
    - validation_score: float - điểm tổng thể (0-1)
    - warnings: List[str] - cảnh báo nếu có
    - errors: List[str] - lỗi nếu có
    """
    result = {
        "success": False,
        "claims": [],
        "resolved_claims": [],
        "validation_score": 0.0,
        "warnings": [],
        "errors": [],
        "article_title": "",
        "timestamp": datetime.now().isoformat(),
        "web_validation": {
            "enabled": False,
            "web_claims_count": 0,
            "validation_results": []
        }
    }
    
    if not AGRI_AGENT_AVAILABLE:
        result["errors"].append(
            f"Agri-Agent không khả dụng. Lỗi import: {IMPORT_ERROR}\n"
            f"Kiểm tra: GOOGLE_API_KEY đã được thiết lập chưa?"
        )
        return result
    
    # Đọc file markdown
    try:
        article_file = Path(article_path)
        if not article_file.exists():
            result["errors"].append(f"File không tồn tại: {article_path}")
            return result
        
        with open(article_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except Exception as e:
        result["errors"].append(f"Lỗi đọc file: {str(e)}")
        return result
    
    # Trích xuất title từ markdown
    title_match = re.search(r'^#\s+(.+)$', markdown_content, re.MULTILINE)
    if title_match:
        result["article_title"] = title_match.group(1).strip()
    
    # Trích xuất text thuần từ markdown
    text_content = extract_text_from_markdown(markdown_content)
    
    if len(text_content) < 100:
        result["warnings"].append("Nội dung bài viết quá ngắn, có thể không đủ thông tin để validate")
    
    # Bước 1: Extract claims từ text
    try:
        # Tối ưu: Tắt chunking cho bài viết ngắn để tiết kiệm API calls
        # Chỉ dùng chunking nếu bài viết > 3000 ký tự
        claims = extract_claims_from_text(
            text_content,
            use_chunking=len(text_content) > 3000,
            chunk_size=3000  # Tăng chunk size để ít chunks hơn
        )
        result["claims"] = [
            {
                "subject": c.subject,
                "predicate": c.predicate,
                "object": c.object,
                "context": c.context,
                "confidence": c.confidence
            }
            for c in claims
        ]
    except Exception as e:
        error_str = str(e)
        # Kiểm tra nếu là lỗi quota
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            result["errors"].append(
                f"❌ Quota API đã hết (20 requests/ngày cho Free tier).\n"
                f"Lỗi: {error_str}\n\n"
                f"💡 Giải pháp:\n"
                f"1. Đợi 24 giờ để reset quota\n"
                f"2. Hoặc nâng cấp lên Paid tier tại https://ai.google.dev/pricing\n"
                f"3. Hoặc thử lại sau vài phút (có thể retry tự động)"
            )
        else:
            result["errors"].append(f"Lỗi khi extract claims: {error_str}")
        return result
    
    if not claims:
        result["warnings"].append("Không trích xuất được claim nào từ bài viết")
        result["success"] = True  # Vẫn thành công nhưng không có claim
        return result
    
    # Bước 2: Tìm kiếm web để validate với nguồn bên ngoài (nếu bật)
    web_claims: List[AgriClaim] = []
    web_validation_results: List[Dict] = []
    
    if use_web_validation:
        try:
            # Lấy subject chính từ bài viết (thường là title hoặc subject phổ biến nhất)
            subject_counts = {}
            for c in claims:
                subject_counts[c.subject] = subject_counts.get(c.subject, 0) + 1
            main_subject = max(subject_counts.items(), key=lambda x: x[1])[0] if subject_counts else result.get("article_title", "")
            
            if main_subject:
                # Tìm kiếm web về subject này
                try:
                    workflow_state = run_agri_workflow(crop=main_subject)
                    web_claims = workflow_state.get("claims", [])
                    
                    # Chỉ validate các claims quan trọng với web (tác giả, giải thưởng, nguồn gốc)
                    important_predicates = [
                        "tác giả", "nguồn gốc", "giải thưởng", "thành tích", "danh hiệu",
                        "tác giả/nguồn gốc", "giải thưởng/thành tích"
                    ]
                    
                    # So sánh claims từ bài viết với claims từ web
                    for article_claim in claims:
                        # Chỉ validate các claims quan trọng
                        predicate_lower = article_claim.predicate.strip().lower()
                        is_important = any(imp in predicate_lower for imp in important_predicates)
                        
                        if not is_important:
                            continue
                        
                        # Tìm claims tương tự từ web (cùng subject và predicate)
                        similar_web_claims = [
                            wc for wc in web_claims
                            if (wc.subject.strip().lower() == article_claim.subject.strip().lower() and
                                wc.predicate.strip().lower() == article_claim.predicate.strip().lower())
                        ]
                        
                        if similar_web_claims:
                            # So sánh với từng claim từ web
                            for web_claim in similar_web_claims:
                                judgment = judge_claims(
                                    article_claim,
                                    web_claim,
                                    use_embedding=True,
                                    use_cache=True
                                )
                                
                                web_validation_results.append({
                                    "article_claim": {
                                        "subject": article_claim.subject,
                                        "predicate": article_claim.predicate,
                                        "object": article_claim.object
                                    },
                                    "web_claim": {
                                        "subject": web_claim.subject,
                                        "predicate": web_claim.predicate,
                                        "object": web_claim.object,
                                        "source_url": web_claim.source_url
                                    },
                                    "relation": judgment["relation"],
                                    "confidence": judgment["confidence"],
                                    "reasoning": judgment["reasoning"]
                                })
                                
                                # Nếu phát hiện contradiction, thêm warning
                                if judgment["relation"] == "CONTRADICTED":
                                    result["warnings"].append(
                                        f"⚠️ Mâu thuẫn phát hiện: '{article_claim.subject} - {article_claim.predicate}: {article_claim.object}' "
                                        f"khác với nguồn web '{web_claim.object}' "
                                        f"(Nguồn: {web_claim.source_url or 'N/A'})"
                                    )
                except Exception as e:
                    # Nếu web search thất bại, vẫn tiếp tục với validation nội bộ
                    result["warnings"].append(f"Không thể tìm kiếm web để validate: {str(e)}")
        except Exception as e:
            result["warnings"].append(f"Lỗi khi validate với web: {str(e)}")
    
    # Gộp claims từ bài viết và web để resolve
    all_claims_for_resolve = claims + web_claims
    
    # Bước 3: Resolve claims (validate bằng Weighted Voting)
    try:
        resolved_claims = group_and_resolve_claims(all_claims_for_resolve)
        result["resolved_claims"] = [
            {
                "subject": rc.gold_claim.subject,
                "predicate": rc.gold_claim.predicate,
                "object": rc.gold_claim.object,
                "context": rc.gold_claim.context,
                "confidence": rc.gold_claim.confidence,
                "total_score": rc.total_score,
                "support_urls": rc.support_urls,
                "cluster_values": rc.cluster_values,
                "has_contradictions": getattr(rc, 'has_contradictions', False),
                "contradiction_details": getattr(rc, 'contradiction_details', [])
            }
            for rc in resolved_claims
        ]
        
        # Kiểm tra tổng thể có contradictions không
        total_contradictions = sum(
            1 for rc in resolved_claims 
            if getattr(rc, 'has_contradictions', False)
        )
        if total_contradictions > 0:
            result["warnings"].append(
                f"⚠️ Phát hiện {total_contradictions} claim có mâu thuẫn. "
                "Vui lòng kiểm tra lại nguồn thông tin."
            )
    except Exception as e:
        result["errors"].append(f"Lỗi khi resolve claims: {str(e)}")
        return result
    
    # Cập nhật thông tin web validation
    if use_web_validation:
        result["web_validation"] = {
            "enabled": True,
            "web_claims_count": len(web_claims),
            "validation_results": web_validation_results
        }
    
    # Bước 4: Tính validation score
    # Score = trung bình confidence của resolved claims
    if resolved_claims:
        avg_confidence = sum(rc.gold_claim.confidence for rc in resolved_claims) / len(resolved_claims)
        avg_score = sum(rc.total_score for rc in resolved_claims) / len(resolved_claims)
        result["validation_score"] = (avg_confidence * 0.6 + avg_score * 0.4)  # Weighted average
    else:
        result["validation_score"] = 0.0
    
    # Bước 5: Phân tích và cảnh báo
    low_confidence_claims = [c for c in claims if c.confidence < 0.5]
    if low_confidence_claims:
        result["warnings"].append(
            f"Có {len(low_confidence_claims)} claim có độ tin cậy thấp (<0.5). "
            "Nên kiểm tra lại nguồn thông tin."
        )
    
    # Kiểm tra claims có object (số liệu cụ thể)
    claims_without_object = [c for c in claims if not c.object]
    if len(claims_without_object) > len(claims) * 0.5:
        result["warnings"].append(
            "Hơn 50% claims không có số liệu cụ thể. "
            "Bài viết có thể thiếu thông tin định lượng quan trọng."
        )
    
    result["success"] = True
    return result


def validate_all_articles(pages_dir: str = "pages") -> Dict[str, Any]:
    """
    Validate tất cả bài viết trong thư mục pages.
    
    Returns
    -------
    Dict chứa:
    - total_articles: int
    - validated_articles: List[Dict] - kết quả từng bài
    - summary: Dict - thống kê tổng hợp
    """
    pages_path = Path(pages_dir)
    if not pages_path.exists():
        return {
            "total_articles": 0,
            "validated_articles": [],
            "summary": {},
            "error": f"Thư mục {pages_dir} không tồn tại"
        }
    
    markdown_files = list(pages_path.glob("*.md"))
    
    results = {
        "total_articles": len(markdown_files),
        "validated_articles": [],
        "summary": {
            "total_claims": 0,
            "total_resolved_claims": 0,
            "avg_validation_score": 0.0,
            "articles_with_warnings": 0,
            "articles_with_errors": 0
        }
    }
    
    for md_file in markdown_files:
        validation_result = validate_wiki_article(str(md_file))
        validation_result["file_path"] = str(md_file)
        validation_result["file_name"] = md_file.name
        results["validated_articles"].append(validation_result)
        
        # Cập nhật summary
        if validation_result["success"]:
            results["summary"]["total_claims"] += len(validation_result["claims"])
            results["summary"]["total_resolved_claims"] += len(validation_result["resolved_claims"])
            if validation_result["warnings"]:
                results["summary"]["articles_with_warnings"] += 1
        else:
            results["summary"]["articles_with_errors"] += 1
    
    # Tính trung bình validation score
    successful_validations = [
        v for v in results["validated_articles"]
        if v["success"] and v["validation_score"] > 0
    ]
    if successful_validations:
        results["summary"]["avg_validation_score"] = sum(
            v["validation_score"] for v in successful_validations
        ) / len(successful_validations)
    
    return results


def get_validation_summary(validation_result: Dict[str, Any]) -> str:
    """
    Tạo báo cáo tóm tắt dễ đọc từ kết quả validation.
    """
    if not validation_result["success"]:
        return f"❌ Validation thất bại: {', '.join(validation_result['errors'])}"
    
    lines = []
    lines.append(f"📄 Bài viết: {validation_result.get('article_title', 'N/A')}")
    lines.append(f"✅ Trạng thái: Thành công")
    lines.append(f"📊 Điểm validation: {validation_result['validation_score']:.2%}")
    lines.append(f"🔍 Số claims trích xuất: {len(validation_result['claims'])}")
    lines.append(f"✨ Số claims đã validate: {len(validation_result['resolved_claims'])}")
    
    if validation_result["warnings"]:
        lines.append(f"⚠️ Cảnh báo ({len(validation_result['warnings'])}):")
        for warning in validation_result["warnings"]:
            lines.append(f"   - {warning}")
    
    if validation_result["resolved_claims"]:
        lines.append("\n📋 Top claims đã validate:")
        for i, rc in enumerate(validation_result["resolved_claims"][:5], 1):
            claim_line = f"   {i}. {rc['subject']} - {rc['predicate']}: {rc['object']} "
            claim_line += f"(Score: {rc['total_score']:.2f})"
            
            # Thêm cảnh báo nếu có contradictions
            if rc.get('has_contradictions'):
                claim_line += " ⚠️ CÓ MÂU THUẪN"
            
            lines.append(claim_line)
        
        # Hiển thị chi tiết contradictions
        contradictions_found = [
            rc for rc in validation_result["resolved_claims"]
            if rc.get('has_contradictions') and rc.get('contradiction_details')
        ]
        
        if contradictions_found:
            lines.append("\n⚠️ CHI TIẾT MÂU THUẪN:")
            for rc in contradictions_found:
                for detail in rc.get('contradiction_details', [])[:2]:  # Chỉ hiển thị 2 đầu tiên
                    lines.append(f"   - {detail.get('claim1', 'N/A')}")
                    lines.append(f"     vs {detail.get('claim2', 'N/A')}")
                    lines.append(f"     Lý do: {detail.get('reasoning', 'N/A')}")
                    lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    """Test validator"""
    print("🧪 Testing Wiki Article Validator")
    print("=" * 50)
    
    if not AGRI_AGENT_AVAILABLE:
        print(f"❌ Agri-Agent không khả dụng: {IMPORT_ERROR}")
        print("\n💡 Hướng dẫn:")
        print("1. Đảm bảo agri-agent-system đã được cài đặt")
        print("2. Thiết lập GOOGLE_API_KEY trong environment")
        sys.exit(1)
    
    # Test với một bài viết mẫu
    pages_dir = Path("pages")
    if pages_dir.exists():
        md_files = list(pages_dir.glob("*.md"))
        if md_files:
            test_file = md_files[0]
            print(f"\n📄 Testing với: {test_file.name}")
            result = validate_wiki_article(str(test_file))
            print("\n" + get_validation_summary(result))
        else:
            print("❌ Không tìm thấy file markdown nào trong pages/")
    else:
        print("❌ Thư mục pages/ không tồn tại")
