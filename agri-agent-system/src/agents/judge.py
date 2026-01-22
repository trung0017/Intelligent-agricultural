"""
NLI Judge: Phát hiện mâu thuẫn giữa các claims bằng LLM và Embedding.

Tính năng:
- Sử dụng Gemini để phát hiện contradictions (NLI Judge)
- Sử dụng embedding models để semantic comparison
- Cache kết quả để tiết kiệm API calls
"""

from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple
import pickle

import numpy as np

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage

from src.models import AgriClaim


# Cache directory
CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "judge_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


NLI_JUDGE_SYSTEM_PROMPT = """Bạn là Thẩm phán Logic (NLI Judge) chuyên về dữ liệu nông nghiệp Việt Nam.
Nhiệm vụ: So sánh hai mệnh đề để phát hiện mâu thuẫn logic.

Quy tắc:
- SUPPORTED: Hai mệnh đề có ý nghĩa tương đương hoặc bổ sung cho nhau
- CONTRADICTED: Hai mệnh đề mâu thuẫn nhau về cùng một sự kiện/thuộc tính
- NEUTRAL: Hai mệnh đề không liên quan hoặc về chủ đề khác nhau

Ví dụ:
- "Giải nhất" vs "Giải khuyến khích" → CONTRADICTED (cùng cuộc thi, khác giải)
- "8.5 tấn/ha" vs "8.6 tấn/ha" → SUPPORTED (số liệu xấp xỉ)
- "Lúa ST25" vs "Lúa ST24" → NEUTRAL (khác giống lúa)

Trả về JSON với format:
{
  "relation": "SUPPORTED" | "CONTRADICTED" | "NEUTRAL",
  "confidence": 0.0-1.0,
  "reasoning": "Giải thích ngắn gọn"
}
"""


def _get_gemini_client() -> ChatGoogleGenerativeAI:
    """Lấy Gemini client cho NLI Judge."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY chưa được thiết lập")
    
    return ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        api_key=api_key,
        temperature=0.1,  # Thấp để có kết quả nhất quán
    )


def _get_embedding_model() -> Optional[GoogleGenerativeAIEmbeddings]:
    """Lấy embedding model cho semantic comparison."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    
    try:
        return GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key,
        )
    except Exception:
        return None


def _get_cache_key(claim1: AgriClaim, claim2: AgriClaim) -> str:
    """Tạo cache key từ 2 claims."""
    # Tạo key từ subject, predicate, object (không phụ thuộc vào confidence, context)
    key_str = f"{claim1.subject}|{claim1.predicate}|{claim1.object}|{claim2.subject}|{claim2.predicate}|{claim2.object}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _load_from_cache(cache_key: str) -> Optional[Dict]:
    """Load kết quả từ cache."""
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    if cache_file.exists():
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None
    return None


def _save_to_cache(cache_key: str, result: Dict) -> None:
    """Lưu kết quả vào cache."""
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(result, f)
    except Exception:
        pass  # Bỏ qua lỗi cache


def _semantic_similarity_embedding(
    text1: str, 
    text2: str, 
    embedding_model: GoogleGenerativeAIEmbeddings
) -> float:
    """
    Tính độ tương đồng semantic bằng embedding.
    Returns: 0.0-1.0 (1.0 = giống nhau hoàn toàn)
    """
    try:
        emb1 = embedding_model.embed_query(text1)
        emb2 = embedding_model.embed_query(text2)
        
        # Cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    except Exception:
        return 0.0


def _simple_text_similarity(text1: str, text2: str) -> float:
    """
    Tính độ tương đồng đơn giản bằng string matching (fallback).
    """
    from difflib import SequenceMatcher
    
    text1 = (text1 or "").strip().lower()
    text2 = (text2 or "").strip().lower()
    
    if text1 == text2:
        return 1.0
    
    return SequenceMatcher(None, text1, text2).ratio()


def judge_claims(
    claim1: AgriClaim,
    claim2: AgriClaim,
    use_embedding: bool = True,
    use_cache: bool = True
) -> Dict:
    """
    So sánh 2 claims và phát hiện mâu thuẫn.
    
    Parameters
    ----------
    claim1, claim2: AgriClaim
        Hai claims cần so sánh
    use_embedding: bool
        Sử dụng embedding để semantic comparison trước khi gọi LLM
    use_cache: bool
        Sử dụng cache để tránh gọi API nhiều lần
    
    Returns
    -------
    Dict với keys:
        - relation: "SUPPORTED" | "CONTRADICTED" | "NEUTRAL"
        - confidence: float (0.0-1.0)
        - reasoning: str
        - from_cache: bool
    """
    # Kiểm tra cache trước
    if use_cache:
        cache_key = _get_cache_key(claim1, claim2)
        cached_result = _load_from_cache(cache_key)
        if cached_result:
            cached_result["from_cache"] = True
            return cached_result
    
    result = {
        "relation": "NEUTRAL",
        "confidence": 0.5,
        "reasoning": "",
        "from_cache": False
    }
    
    # Bước 1: Kiểm tra nhanh - nếu subject/predicate khác nhau → NEUTRAL
    if (claim1.subject.strip().lower() != claim2.subject.strip().lower() or
        claim1.predicate.strip().lower() != claim2.predicate.strip().lower()):
        result["relation"] = "NEUTRAL"
        result["reasoning"] = "Khác subject hoặc predicate"
        result["confidence"] = 1.0
        if use_cache:
            _save_to_cache(cache_key, result)
        return result
    
    # Bước 2: Kiểm tra object giống nhau hoàn toàn → SUPPORTED
    obj1 = (claim1.object or "").strip()
    obj2 = (claim2.object or "").strip()
    
    if obj1 and obj2:
        if obj1.lower() == obj2.lower():
            result["relation"] = "SUPPORTED"
            result["reasoning"] = "Giá trị giống nhau hoàn toàn"
            result["confidence"] = 1.0
            if use_cache:
                _save_to_cache(cache_key, result)
            return result
    
    # Bước 3: Semantic similarity check (nếu có embedding)
    if use_embedding and obj1 and obj2:
        embedding_model = _get_embedding_model()
        if embedding_model:
            similarity = _semantic_similarity_embedding(obj1, obj2, embedding_model)
            
            # Nếu similarity rất cao (>0.95) → SUPPORTED
            if similarity > 0.95:
                result["relation"] = "SUPPORTED"
                result["reasoning"] = f"Giá trị tương đồng cao (similarity: {similarity:.2f})"
                result["confidence"] = similarity
                if use_cache:
                    _save_to_cache(cache_key, result)
                return result
            
            # Nếu similarity rất thấp (<0.3) và cùng predicate → có thể CONTRADICTED
            # Nhưng cần LLM để xác nhận
        else:
            # Fallback: string similarity
            similarity = _simple_text_similarity(obj1, obj2)
            if similarity > 0.9:
                result["relation"] = "SUPPORTED"
                result["reasoning"] = f"Giá trị tương đồng (similarity: {similarity:.2f})"
                result["confidence"] = similarity
                if use_cache:
                    _save_to_cache(cache_key, result)
                return result
    
    # Bước 4: Gọi LLM để phát hiện mâu thuẫn (NLI Judge)
    try:
        client = _get_gemini_client()
        
        # Format claims
        claim1_str = f"{claim1.subject} - {claim1.predicate}: {claim1.object}"
        if claim1.context:
            claim1_str += f" (Context: {claim1.context})"
        
        claim2_str = f"{claim2.subject} - {claim2.predicate}: {claim2.object}"
        if claim2.context:
            claim2_str += f" (Context: {claim2.context})"
        
        prompt = f"""Mệnh đề 1: {claim1_str}
Mệnh đề 2: {claim2_str}

Hãy phân tích và trả về JSON theo format đã quy định."""
        
        messages = [
            SystemMessage(content=NLI_JUDGE_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        response = client.invoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        
        # Parse JSON
        try:
            # Tìm JSON trong response
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                json_str = content[start:end+1]
                llm_result = json.loads(json_str)
                
                result["relation"] = llm_result.get("relation", "NEUTRAL")
                result["confidence"] = float(llm_result.get("confidence", 0.5))
                result["reasoning"] = llm_result.get("reasoning", "")
            else:
                # Fallback: tìm keywords trong response
                content_lower = content.lower()
                if "contradicted" in content_lower or "mâu thuẫn" in content_lower:
                    result["relation"] = "CONTRADICTED"
                elif "supported" in content_lower or "trùng khớp" in content_lower:
                    result["relation"] = "SUPPORTED"
                result["reasoning"] = content[:200]  # Lấy 200 ký tự đầu
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback: phân tích đơn giản
            if obj1 and obj2:
                # Kiểm tra các từ khóa mâu thuẫn
                contradiction_keywords = [
                    ("giải nhất", "giải khuyến khích"),
                    ("giải nhất", "giải nhì"),
                    ("giải nhất", "giải ba"),
                    ("có", "không có"),
                    ("đúng", "sai"),
                ]
                
                for kw1, kw2 in contradiction_keywords:
                    if (kw1 in obj1.lower() and kw2 in obj2.lower()) or \
                       (kw2 in obj1.lower() and kw1 in obj2.lower()):
                        result["relation"] = "CONTRADICTED"
                        result["reasoning"] = f"Phát hiện từ khóa mâu thuẫn: {kw1} vs {kw2}"
                        result["confidence"] = 0.7
                        break
                
                if result["relation"] == "NEUTRAL":
                    result["reasoning"] = f"Không thể parse kết quả từ LLM: {str(e)}"
    except Exception as e:
        # Fallback cuối cùng
        result["reasoning"] = f"Lỗi khi gọi LLM: {str(e)}"
        result["confidence"] = 0.3
    
    # Lưu vào cache
    if use_cache:
        _save_to_cache(cache_key, result)
    
    return result


def detect_contradictions_in_group(
    claims: List[AgriClaim],
    use_embedding: bool = True,
    use_cache: bool = True
) -> Dict:
    """
    Phát hiện contradictions trong một nhóm claims.
    
    Parameters
    ----------
    claims: List[AgriClaim]
        Danh sách claims cần kiểm tra
    use_embedding: bool
        Sử dụng embedding để semantic comparison
    use_cache: bool
        Sử dụng cache
    
    Returns
    -------
    Dict với keys:
        - has_contradictions: bool
        - contradiction_pairs: List[Tuple[int, int]] (indices)
        - contradiction_details: List[Dict]
        - all_relations: Dict[Tuple[int, int], str] (map cặp claims -> relation)
    """
    if len(claims) < 2:
        return {
            "has_contradictions": False,
            "contradiction_pairs": [],
            "contradiction_details": [],
            "all_relations": {}
        }
    
    contradictions = []
    details = []
    all_relations = {}
    
    # So sánh từng cặp
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            result = judge_claims(
                claims[i], 
                claims[j],
                use_embedding=use_embedding,
                use_cache=use_cache
            )
            
            relation = result["relation"]
            all_relations[(i, j)] = relation
            
            if relation == "CONTRADICTED":
                contradictions.append((i, j))
                details.append({
                    "claim1_index": i,
                    "claim2_index": j,
                    "claim1": f"{claims[i].subject} - {claims[i].predicate}: {claims[i].object}",
                    "claim2": f"{claims[j].subject} - {claims[j].predicate}: {claims[j].object}",
                    "reasoning": result["reasoning"],
                    "confidence": result["confidence"],
                    "from_cache": result.get("from_cache", False)
                })
    
    return {
        "has_contradictions": len(contradictions) > 0,
        "contradiction_pairs": contradictions,
        "contradiction_details": details,
        "all_relations": all_relations
    }


def cluster_claims_by_semantic_similarity(
    claims: List[AgriClaim],
    similarity_threshold: float = 0.85
) -> List[List[AgriClaim]]:
    """
    Cluster claims theo semantic similarity.
    
    Parameters
    ----------
    claims: List[AgriClaim]
        Danh sách claims
    similarity_threshold: float
        Ngưỡng similarity để coi là cùng cluster (0.85 = 85%)
    
    Returns
    -------
    List[List[AgriClaim]]: Các clusters
    """
    if not claims:
        return []
    
    embedding_model = _get_embedding_model()
    clusters: List[List[AgriClaim]] = []
    
    for claim in claims:
        claim_value = f"{claim.subject} - {claim.predicate}: {claim.object or ''}"
        
        matched = False
        for cluster in clusters:
            # So sánh với claim đầu tiên trong cluster
            cluster_value = f"{cluster[0].subject} - {cluster[0].predicate}: {cluster[0].object or ''}"
            
            # Kiểm tra giống nhau hoàn toàn
            if claim_value.lower() == cluster_value.lower():
                cluster.append(claim)
                matched = True
                break
            
            # Semantic similarity
            if embedding_model:
                similarity = _semantic_similarity_embedding(
                    claim_value,
                    cluster_value,
                    embedding_model
                )
            else:
                similarity = _simple_text_similarity(
                    claim.object or "",
                    cluster[0].object or ""
                )
            
            if similarity >= similarity_threshold:
                cluster.append(claim)
                matched = True
                break
        
        if not matched:
            clusters.append([claim])
    
    return clusters


__all__ = [
    "judge_claims",
    "detect_contradictions_in_group",
    "cluster_claims_by_semantic_similarity",
]
