from __future__ import annotations

"""
Workflow LangGraph chính cho Agri-Agent.

Luồng cơ bản (v1, tối giản để demo end‑to‑end):
- Search (DuckDuckGo)  -> lấy danh sách URL liên quan tới cây trồng/ngữ cảnh.
- Extract (Extractor Agent) -> trích xuất AgriClaim từ từng URL.
- Resolve (Resolver Agent)  -> hợp nhất claim bằng Weighted Voting.
- Writer (Summary)          -> tạo tóm tắt thân thiện cho người dùng.

Ghi chú:
- Giai đoạn NLI Judge trong PROMPTS.md chưa được hiện thực riêng,
  nên tạm thời được gộp logic vào Resolver/Writer.
"""

from typing import Any, Dict, List, Optional, TypedDict
from urllib.parse import urlparse
import os

from duckduckgo_search import DDGS

from src.agents.extractor import extract_claims_from_url
from src.agents.resolver import ResolvedClaim, group_and_resolve_claims
from src.models import AgriClaim
from src.tools.filter import calculate_trust_score

from langgraph.graph import END, StateGraph

# Thử import Tavily nếu có
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False


class WorkflowState(TypedDict, total=False):
    """
    Trạng thái luồng LangGraph cho một lần truy vấn.

    Các trường:
    - crop: Tên cây trồng/đối tượng phân tích do người dùng nhập.
    - query: Câu truy vấn mở rộng để search web.
    - search_results: Danh sách URL thu được từ search.
    - claims: Danh sách claim thô (AgriClaim) từ nhiều nguồn.
    - resolved_claims: Danh sách claim đã được hợp nhất (ResolvedClaim).
    - summary: Chuỗi tóm tắt kết quả cuối cùng cho người dùng.
    - debug_info: Thông tin phụ (số URL/claim, lỗi nếu có, ...).
    """

    crop: str
    query: str
    search_results: List[str]
    claims: List[AgriClaim]
    resolved_claims: List[ResolvedClaim]
    summary: str
    debug_info: Dict[str, Any]


# Một số domain cần loại bỏ hoàn toàn (forum, spam, không liên quan nông nghiệp)
DISALLOWED_HOSTS = {
    "vfo.vn",
}


def _build_search_query(crop: str) -> str:
    """
    Sinh câu truy vấn tiếng Việt thân thiện cho DuckDuckGo.
    Loại bỏ dấu ngoặc kép để tránh vấn đề với DuckDuckGo.
    """
    crop = crop.strip()
    if not crop:
        return "giống lúa năng suất cao ĐBSCL"
    # Query đơn giản hơn, không dùng dấu ngoặc kép
    return f"{crop} năng suất giống lúa"


def search_node(state: WorkflowState) -> WorkflowState:
    """
    Node Search: dùng DuckDuckGo để tìm các URL phù hợp.
    """
    crop = state.get("crop", "").strip()
    query = state.get("query") or _build_search_query(crop)

    urls: List[str] = []
    debug: Dict[str, Any] = dict(state.get("debug_info") or {})

    def _run_ddg(q: str, *, region: Optional[str] = None) -> List[str]:
        """Chạy DuckDuckGo search và trả về danh sách URL."""
        out: List[str] = []
        try:
            with DDGS() as ddgs:
                # Với query tiếng Việt, region "vn-vi" thường cho kết quả tốt hơn
                # Nếu không có region, thường trả về 0 kết quả cho tiếng Việt
                if region:
                    results = ddgs.text(
                        q,
                        region=region,
                        safesearch="moderate",
                        max_results=15,  # Tăng lên để có nhiều lựa chọn hơn
                    )
                else:
                    results = ddgs.text(
                        q,
                        safesearch="moderate",
                        max_results=15,
                    )
                # Chuyển iterator sang list để có thể đếm và debug
                results_list = list(results)
                debug.setdefault("ddg_raw_results_count", []).append({
                    "query": q,
                    "region": region or "default",
                    "count": len(results_list),
                    "sample_urls": [r.get("href") or r.get("url") or "N/A" for r in results_list[:3]]
                })
                for r in results_list:
                    href = r.get("href") or r.get("url")
                    if href:
                        # Lọc ngay một số domain không phù hợp
                        host = urlparse(href).netloc.lower()
                        if any(bad in host for bad in ["vfo.vn", "zhihu.com", "yahoo", "seek.com", "forum"]):
                            continue
                        out.append(href)
        except Exception as exc:
            # Log lỗi nhưng không raise, để có thể thử fallback queries
            error_msg = f"DuckDuckGo search error for query '{q}' (region={region}): {exc}"
            debug.setdefault("errors", []).append(error_msg)
        return out

    def _run_tavily(q: str) -> List[str]:
        """Chạy Tavily search nếu có API key."""
        if not TAVILY_AVAILABLE:
            return []
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return []
        try:
            client = TavilyClient(api_key=api_key)
            response = client.search(q, max_results=10, search_depth="basic")
            urls = [result.get("url") for result in response.get("results", []) if result.get("url")]
            return urls
        except Exception as exc:
            debug.setdefault("errors", []).append(f"Tavily search error for query '{q}': {exc}")
            return []

    try:
        # Với query tiếng Việt, region "vn-vi" thường cho kết quả tốt hơn
        # Strategy: Ưu tiên region "vn-vi" cho query tiếng Việt
        
        # 1) Query chính với region vn-vi (quan trọng cho tiếng Việt)
        urls = _run_ddg(query, region="vn-vi")
        debug["ddg_results_initial_vn_vi"] = len(urls)

        # 2) Nếu không có kết quả, thử query đơn giản hơn với region vn-vi
        if not urls and crop:
            simple_query = f"{crop} năng suất"
            debug["fallback_query_simple"] = simple_query
            urls = _run_ddg(simple_query, region="vn-vi")
            debug["ddg_results_simple_fallback"] = len(urls)

        # 3) Thử chỉ tên cây trồng với region vn-vi
        if not urls and crop:
            crop_only = crop
            debug["fallback_query_crop_only"] = crop_only
            urls = _run_ddg(crop_only, region="vn-vi")
            debug["ddg_results_crop_only"] = len(urls)

        # 4) Thử query tiếng Anh không có region (toàn cầu)
        if not urls and crop:
            global_query = f"{crop} rice yield Vietnam"
            debug["fallback_query_en"] = global_query
            urls = _run_ddg(global_query, region=None)
            debug["ddg_results_en_fallback"] = len(urls)

        # 5) Thử query tiếng Anh đơn giản hơn
        if not urls and crop:
            simple_en = "ST25 rice variety Vietnam"
            debug["fallback_query_simple_en"] = simple_en
            urls = _run_ddg(simple_en, region=None)
            debug["ddg_results_simple_en"] = len(urls)

        # 6) Fallback cuối cùng: Tavily (nếu có API key)
        if not urls and crop:
            tavily_query = f"{crop} năng suất giống lúa"
            debug["tavily_query"] = tavily_query
            urls = _run_tavily(tavily_query)
            debug["tavily_results"] = len(urls)

    except Exception as exc:  # pragma: no cover - phụ thuộc network
        debug.setdefault("errors", []).append(f"Search error: {exc}")

    # Loại bỏ trùng lặp và bỏ các domain nằm trong blacklist
    # Cũng loại bỏ các URL không hợp lệ (relative URLs, không có scheme)
    dedup_urls: List[str] = []
    for u in urls:
        if not u or not u.strip():
            continue
        try:
            parsed = urlparse(u)
            # Bỏ qua URL không có scheme (http/https) hoặc không có netloc (relative URLs)
            if not parsed.scheme or not parsed.netloc:
                continue
            # Chỉ chấp nhận http và https
            if parsed.scheme not in ["http", "https"]:
                continue
            host = parsed.netloc.split(":", 1)[0].lower()
            if host in DISALLOWED_HOSTS:
                continue
            if u not in dedup_urls:
                dedup_urls.append(u)
        except Exception:
            # Bỏ qua URL không hợp lệ
            continue

    debug["num_urls_after_dedup"] = len(dedup_urls)

    # Lọc theo trust_score để tránh domain rác / forum / spam
    # Với DuckDuckGo, kết quả thường có trust_score thấp, nên giảm ngưỡng xuống 0.3
    # Sau đó sẽ dùng scraper để kiểm tra nội dung thực tế
    filtered_urls: List[str] = []
    trust_scores_detail: List[Dict[str, Any]] = []
    for u in dedup_urls:
        score = calculate_trust_score(u)
        trust_scores_detail.append({"url": u, "trust_score": score})
        # Giảm ngưỡng xuống 0.3 để lấy nhiều kết quả hơn
        # Sẽ filter lại sau khi scrape và extract claims
        if score >= 0.3:
            filtered_urls.append(u)

    debug["num_urls_after_trust_filter"] = len(filtered_urls)
    debug["trust_scores_detail"] = trust_scores_detail[:20]  # Giới hạn log

    # Nếu sau khi lọc không còn gì, dùng lại danh sách gốc (đã dedup) như fallback
    # Nhưng chỉ lấy 10 URL đầu tiên
    final_urls = filtered_urls if filtered_urls else dedup_urls
    final_urls = final_urls[:15]  # Tăng lên 15 để có nhiều cơ hội extract claims hơn

    debug["search_query"] = query
    debug["num_search_results"] = len(final_urls)
    debug["filtered_domains"] = [
        {"url": u, "trust_score": calculate_trust_score(u)} for u in final_urls
    ]

    return {
        **state,
        "query": query,
        "search_results": final_urls,
        "debug_info": debug,
    }


def extract_node(state: WorkflowState) -> WorkflowState:
    """
    Node Extract: chạy Extractor Agent để trích xuất claim từ từng URL.
    """
    urls = state.get("search_results") or []
    all_claims: List[AgriClaim] = []
    debug: Dict[str, Any] = dict(state.get("debug_info") or {})
    errors: List[str] = list(debug.get("errors") or [])

    for url in urls:
        try:
            claims = extract_claims_from_url(url)
            all_claims.extend(claims)
        except Exception as exc:  # pragma: no cover - phụ thuộc LLM/network
            errors.append(f"Extract error for {url}: {exc}")

    debug["errors"] = errors
    debug["num_claims"] = len(all_claims)

    return {
        **state,
        "claims": all_claims,
        "debug_info": debug,
    }


def resolve_node(state: WorkflowState) -> WorkflowState:
    """
    Node Resolve: hợp nhất các claim bằng thuật toán Weighted Voting
    (đã cài đặt trong Resolver Agent).
    """
    claims = state.get("claims") or []
    debug: Dict[str, Any] = dict(state.get("debug_info") or {})

    resolved: List[ResolvedClaim] = []
    if claims:
        resolved = group_and_resolve_claims(claims)

    debug["num_resolved_claims"] = len(resolved)

    return {
        **state,
        "resolved_claims": resolved,
        "debug_info": debug,
    }


def _format_resolved_claim(rc: ResolvedClaim) -> str:
    """
    Format 1 ResolvedClaim thành một câu/text ngắn.
    """
    c = rc.gold_claim
    parts: List[str] = []

    # Subject + predicate + object
    base = c.subject
    if c.predicate:
        base += f" - {c.predicate}"
    if c.object:
        base += f": {c.object}"
    parts.append(base)

    # Context nếu có
    if c.context:
        parts.append(f"(Bối cảnh: {c.context})")

    # Nguồn hỗ trợ
    if rc.support_urls:
        parts.append(f"Nguồn: {', '.join(rc.support_urls[:3])}")

    return " ".join(parts)


def writer_node(state: WorkflowState) -> WorkflowState:
    """
    Node Writer: tạo tóm tắt thân thiện cho người dùng từ resolved_claims.
    Không dùng LLM để tiết kiệm chi phí, chỉ tổng hợp rule-based.
    """
    crop = state.get("crop", "").strip()
    resolved = state.get("resolved_claims") or []

    if not resolved:
        summary = (
            f"Chưa tìm được thông tin tin cậy cho '{crop}' "
            "từ các nguồn web hiện tại. Vui lòng thử lại với từ khóa cụ thể hơn."
        )
    else:
        lines: List[str] = []
        if crop:
            lines.append(f"Kết quả tổng hợp cho: {crop}")
        else:
            lines.append("Kết quả tổng hợp thông tin nông nghiệp:")

        for idx, rc in enumerate(resolved, start=1):
            lines.append(f"{idx}. {_format_resolved_claim(rc)}")

        summary = "\n".join(lines)

    return {
        **state,
        "summary": summary,
    }


def build_workflow_graph() -> StateGraph:
    """
    Khởi tạo và trả về StateGraph (chưa compile) cho workflow Agri-Agent.
    """
    graph = StateGraph(WorkflowState)
    graph.add_node("search", search_node)
    graph.add_node("extract", extract_node)
    graph.add_node("resolve", resolve_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("search")
    graph.add_edge("search", "extract")
    graph.add_edge("extract", "resolve")
    graph.add_edge("resolve", "writer")
    graph.add_edge("writer", END)

    return graph


def get_compiled_app():
    """
    Trả về đối tượng app LangGraph đã compile, dùng để gọi từ bên ngoài.
    """
    graph = build_workflow_graph()
    return graph.compile()


def run_agri_workflow(
    crop: str,
    *,
    initial_query: Optional[str] = None,
) -> WorkflowState:
    """
    Hàm tiện ích cấp cao: chạy toàn bộ workflow cho một cây trồng/câu hỏi.

    Parameters
    ----------
    crop:
        Tên cây trồng/đối tượng chính (VD: 'Lúa ST25').
    initial_query:
        Nếu muốn tự cung cấp câu query cho search (tuỳ chọn).

    Returns
    -------
    WorkflowState
        Trạng thái cuối cùng sau khi workflow chạy xong
        (bao gồm summary, resolved_claims, debug_info, ...).
    """
    app = get_compiled_app()
    init_state: WorkflowState = {
        "crop": crop,
        "query": initial_query or _build_search_query(crop),
        "search_results": [],
        "claims": [],
        "resolved_claims": [],
        "summary": "",
        "debug_info": {},
    }
    result: WorkflowState = app.invoke(init_state)
    return result


__all__ = [
    "WorkflowState",
    "run_agri_workflow",
    "get_compiled_app",
    "build_workflow_graph",
]

