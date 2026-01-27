from __future__ import annotations

"""
Extractor agent: dùng Gemini 1.5 Flash để trích xuất AgriClaim từ văn bản/URL.

Thiết kế:
- Hàm extract_claims_from_text: gọi LLM với prompt trong PROMPTS.md và parse JSON.
- Hàm extract_claims_from_url: dùng scraper.scrape_clean_text rồi gọi extract_claims_from_text.

Yêu cầu biến môi trường:
- GOOGLE_API_KEY: khóa truy cập Google Gemini 1.5 Flash.
"""

from typing import Iterable, List
import json
import os
import re
import time

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.models import AgriClaim
from src.tools.scraper import scrape_clean_text

# Import rate limiter và circuit breaker
try:
    from src.utils.rate_limiter import get_rate_limiter, get_circuit_breaker
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    # Fallback: tạo dummy functions
    def get_rate_limiter():
        return None
    def get_circuit_breaker():
        return None


EXTRACTION_SYSTEM_PROMPT = (
    "Bạn là Chuyên gia Dữ liệu Nông nghiệp Việt Nam chuyên trích xuất thông tin chi tiết.\n"
    "Nhiệm vụ: Trích xuất TẤT CẢ các khẳng định (Claims) có thể từ văn bản về giống cây trồng/kỹ thuật canh tác.\n\n"
    "QUAN TRỌNG: Bạn phải trích xuất CÀNG NHIỀU claims CÀNG TỐT để đảm bảo double-check thông tin.\n"
    "Hãy trích xuất từ MỌI đoạn văn, MỌI câu có chứa thông tin về:\n"
    "- Số liệu cụ thể (năng suất, thời gian, kích thước, trọng lượng, tỷ lệ...)\n"
    "- Đặc điểm hình thái (màu sắc, hình dạng, kích thước...)\n"
    "- Giải thưởng, thành tích, danh hiệu\n"
    "- Điều kiện canh tác (vụ mùa, vùng địa lý, khí hậu...)\n"
    "- Khả năng chịu đựng (mặn, hạn, lũ, sâu bệnh...)\n"
    "- Chất lượng sản phẩm (mùi vị, độ dẻo, hàm lượng dinh dưỡng...)\n"
    "- Kỹ thuật canh tác (mật độ, phân bón, tưới tiêu...)\n"
    "- Thông tin lịch sử, nguồn gốc, tác giả\n"
    "- So sánh với giống khác\n\n"
    "Yêu cầu Output: trả về một JSON array các object theo schema AgriClaim:\n"
    "{\n"
    '  "subject": "Tên thực thể chính hóa (VD: Lúa ST25, Bệnh đạo ôn)",\n'
    '  "predicate": "Thuộc tính (VD: Năng suất, Thời gian sinh trưởng, Khả năng chịu mặn, Giải thưởng, Đặc điểm hình thái, Mùi vị, Hàm lượng Protein...)",\n'
    '  "object": "Giá trị cụ thể bao gồm đơn vị (VD: 8.5 tấn/ha, 95-100 ngày, Giải nhất cuộc thi...) hoặc mô tả chi tiết nếu không có số liệu",\n'
    '  "context": "Điều kiện áp dụng (VD: Vụ Đông Xuân, Vùng ven biển, Năm 2019...) hoặc null",\n'
    '  "confidence": "Độ tin cậy của mô hình (float 0.0 - 1.0, ưu tiên 0.7+ cho thông tin rõ ràng)"\n'
    "}\n\n"
    "Hướng dẫn trích xuất:\n"
    "- Mỗi câu/đoạn có thể tạo ra 1-3 claims (ví dụ: 'Lúa ST25 đạt 8.5 tấn/ha trong vụ Đông Xuân' → 2 claims: năng suất + vụ mùa)\n"
    "- Trích xuất cả thông tin định tính (màu sắc, mùi vị) và định lượng (số liệu)\n"
    "- Nếu có nhiều giá trị trong một câu, tách thành nhiều claims riêng\n"
    "- Ưu tiên claims có object cụ thể (số liệu hoặc mô tả rõ ràng)\n"
    "- Chỉ trả về JSON hợp lệ, không kèm giải thích.\n"
    "- Nếu không có claim nào, trả về []"
)


def _get_gemini_client() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY chưa được thiết lập trong môi trường. "
            "Hãy cấu hình API key trước khi gọi extractor."
        )

    # Lưu ý:
    # - Model "gemini-1.5-flash" đã bị deprecated và không còn tồn tại (404 NOT_FOUND).
    # - Các model hiện có:
    #   * gemini-2.5-flash: Model mới nhất, nhanh và hiệu quả (ĐÃ VƯỢT LIMIT: 23/20 RPD)
    #   * gemini-flash-latest: Alias luôn trỏ tới model flash mới nhất (ĐÃ VƯỢT LIMIT)
    #   * gemini-2.5-flash-lite: Phiên bản nhẹ hơn (CÒN TRỐNG: 0/10 RPM, 0/20 RPD)
    #   * gemini-3-flash: Model mới (CÒN TRỐNG: 0/5 RPM, 0/20 RPD)
    # - Đổi sang gemini-2.5-flash-lite để tránh vượt rate limit của gemini-2.5-flash
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  # Đổi sang flash-lite để tránh rate limit
        api_key=api_key,
        temperature=0.3,  # Tăng từ 0.2 lên 0.3 để model sáng tạo hơn trong việc tìm claims
    )


def _chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """
    Chia nhỏ văn bản dài thành các đoạn để trích xuất claims tốt hơn.
    
    Args:
        text: Văn bản cần chia nhỏ
        chunk_size: Kích thước mỗi đoạn (số ký tự)
        overlap: Số ký tự chồng lấp giữa các đoạn để không mất thông tin
    
    Returns:
        List các đoạn văn bản
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    # Chia theo câu để tránh cắt giữa câu
    sentences = re.split(r'([.!?]\s+)', text)
    
    current_chunk = ""
    for i in range(0, len(sentences), 2):
        sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
        
        if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Bắt đầu đoạn mới với overlap
            current_chunk = current_chunk[-overlap:] + sentence
        else:
            current_chunk += sentence
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text]


def extract_claims_from_text(text: str, use_chunking: bool = True, chunk_size: int = 2000) -> List[AgriClaim]:
    """
    Trích xuất danh sách AgriClaim từ đoạn văn bản tiếng Việt liên quan nông nghiệp.
    
    Args:
        text: Văn bản cần trích xuất
        use_chunking: Có chia nhỏ văn bản dài thành các đoạn không (mặc định True)
        chunk_size: Kích thước mỗi đoạn khi chia nhỏ (mặc định 2000 ký tự)
    
    Returns:
        List các AgriClaim được trích xuất
    
    Raises:
        RuntimeError: Nếu gặp lỗi quota (429) và đã retry hết số lần
    """
    text = (text or "").strip()
    if not text:
        return []

    # Tối ưu: Tắt chunking cho bài viết ngắn để tiết kiệm API calls
    # Chỉ chunk nếu bài viết > 3000 ký tự (thay vì 2000)
    if use_chunking and len(text) > 3000:
        use_chunking = True
        chunk_size = 3000  # Tăng chunk size để ít chunks hơn
    elif len(text) <= 3000:
        use_chunking = False  # Tắt chunking cho bài viết ngắn

    client = _get_gemini_client()
    
    # Chia nhỏ văn bản dài để trích xuất nhiều claims hơn
    if use_chunking and len(text) > chunk_size:
        chunks = _chunk_text(text, chunk_size=chunk_size)
        all_claims = []
        
        for chunk in chunks:
            # Kiểm tra Circuit Breaker trước khi gọi API
            if RATE_LIMITER_AVAILABLE:
                circuit_breaker = get_circuit_breaker()
                if circuit_breaker and not circuit_breaker.can_make_request():
                    print(f"🚨 Circuit Breaker OPEN: Bỏ qua chunk do quá nhiều lỗi 429")
                    continue
                
                # Rate limiting
                rate_limiter = get_rate_limiter()
                if rate_limiter:
                    rate_limiter.wait_if_needed()
            
            messages = [
                SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=f"Input Text:\n{chunk}"),
            ]
            
            # Retry logic cho lỗi quota (429) - GIẢM số lần retry
            max_retries = 1  # Giảm từ 2 xuống 1 để tránh tạo quá nhiều requests
            raw_content = None
            for attempt in range(max_retries + 1):
                try:
                    # Ghi nhận request (cho circuit breaker)
                    if RATE_LIMITER_AVAILABLE:
                        circuit_breaker = get_circuit_breaker()
                        if circuit_breaker:
                            circuit_breaker.record_request()
                    
                    response = client.invoke(messages)
                    raw_content = response.content if isinstance(response.content, str) else (
                        "".join(part["text"] for part in response.content if isinstance(part, dict) and "text" in part)
                        if isinstance(response.content, Iterable)
                        else str(response.content)
                    )
                    
                    # Ghi nhận success
                    if RATE_LIMITER_AVAILABLE:
                        circuit_breaker = get_circuit_breaker()
                        if circuit_breaker:
                            circuit_breaker.record_success()
                    
                    break  # Thành công, thoát khỏi retry loop
                except Exception as e:
                    error_str = str(e)
                    is_429 = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()
                    
                    # Ghi nhận failure
                    if RATE_LIMITER_AVAILABLE:
                        circuit_breaker = get_circuit_breaker()
                        if circuit_breaker:
                            circuit_breaker.record_failure(is_429=is_429)
                    
                    # Kiểm tra nếu là lỗi quota (429)
                    if is_429 and attempt < max_retries:
                        # Nếu circuit breaker đã mở, không retry nữa
                        if RATE_LIMITER_AVAILABLE:
                            circuit_breaker = get_circuit_breaker()
                            if circuit_breaker and circuit_breaker.get_state().name == "OPEN":
                                print(f"🚨 Circuit Breaker OPEN: Dừng retry do quá nhiều lỗi 429")
                                raw_content = None
                                break
                        
                        # Exponential backoff với jitter
                        import random
                        base_delay = 60  # Tăng lên 60 giây
                        delay = (2 ** attempt) * base_delay  # 60s, 120s
                        jitter = random.uniform(0, 20)  # Tăng jitter lên 0-20s
                        wait_time = delay + jitter
                        
                        try:
                            # Tìm "retry in Xs" hoặc "retryDelay" trong error
                            import re
                            retry_match = re.search(r'retry in ([\d.]+)s', error_str, re.IGNORECASE)
                            if retry_match:
                                wait_time = max(wait_time, float(retry_match.group(1)) + 10)  # Thêm buffer lớn hơn
                            else:
                                retry_delay_match = re.search(r"'retryDelay':\s*'(\d+)s'", error_str)
                                if retry_delay_match:
                                    wait_time = max(wait_time, float(retry_delay_match.group(1)) + 10)
                        except:
                            pass
                        
                        print(f"⚠️ Rate limit hit (429), waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(wait_time)
                        continue
                    # Nếu không phải lỗi quota hoặc đã retry hết, bỏ qua chunk này
                    raw_content = None
                    break
            
            if not raw_content:
                # Bỏ qua chunk này nếu không lấy được content
                continue
            
            try:
                data = json.loads(raw_content)
            except json.JSONDecodeError:
                # Thử tìm đoạn JSON trong output
                start = raw_content.find("[")
                end = raw_content.rfind("]")
                if start == -1 or end == -1 or end <= start:
                    continue
                try:
                    data = json.loads(raw_content[start : end + 1])
                except json.JSONDecodeError:
                    continue
            
            if isinstance(data, list):
                for item in data:
                    try:
                        claim = AgriClaim(**item)
                        all_claims.append(claim)
                    except Exception:
                        continue
        
        # Loại bỏ claims trùng lặp (dựa trên subject + predicate + object)
        seen = set()
        unique_claims = []
        for claim in all_claims:
            key = (claim.subject, claim.predicate, claim.object)
            if key not in seen:
                seen.add(key)
                unique_claims.append(claim)
        
        return unique_claims
    else:
        # Xử lý văn bản ngắn hoặc không chia nhỏ
        messages = [
            SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=f"Input Text:\n{text}"),
        ]

        # Kiểm tra Circuit Breaker trước khi gọi API
        if RATE_LIMITER_AVAILABLE:
            circuit_breaker = get_circuit_breaker()
            if circuit_breaker and not circuit_breaker.can_make_request():
                raise RuntimeError("Circuit Breaker OPEN: Quá nhiều lỗi 429, vui lòng thử lại sau")
            
            # Rate limiting
            rate_limiter = get_rate_limiter()
            if rate_limiter:
                rate_limiter.wait_if_needed()
        
        # Retry logic cho lỗi quota (429) - GIẢM số lần retry
        max_retries = 1  # Giảm từ 2 xuống 1
        for attempt in range(max_retries + 1):
            try:
                # Ghi nhận request
                if RATE_LIMITER_AVAILABLE:
                    circuit_breaker = get_circuit_breaker()
                    if circuit_breaker:
                        circuit_breaker.record_request()
                
                response = client.invoke(messages)
                raw_content = response.content if isinstance(response.content, str) else (
                    "".join(part["text"] for part in response.content if isinstance(part, dict) and "text" in part)
                    if isinstance(response.content, Iterable)
                    else str(response.content)
                )
                
                # Ghi nhận success
                if RATE_LIMITER_AVAILABLE:
                    circuit_breaker = get_circuit_breaker()
                    if circuit_breaker:
                        circuit_breaker.record_success()
                
                break  # Thành công, thoát khỏi retry loop
            except Exception as e:
                error_str = str(e)
                is_429 = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()
                
                # Ghi nhận failure
                if RATE_LIMITER_AVAILABLE:
                    circuit_breaker = get_circuit_breaker()
                    if circuit_breaker:
                        circuit_breaker.record_failure(is_429=is_429)
                
                # Kiểm tra nếu là lỗi quota (429)
                if is_429 and attempt < max_retries:
                    # Nếu circuit breaker đã mở, không retry
                    if RATE_LIMITER_AVAILABLE:
                        circuit_breaker = get_circuit_breaker()
                        if circuit_breaker and circuit_breaker.get_state().name == "OPEN":
                            raise RuntimeError("Circuit Breaker OPEN: Quá nhiều lỗi 429, vui lòng thử lại sau")
                    
                    # Exponential backoff
                    import random
                    base_delay = 60
                    delay = (2 ** attempt) * base_delay
                    jitter = random.uniform(0, 20)
                    wait_time = delay + jitter
                    
                    try:
                        retry_match = re.search(r'retry in ([\d.]+)s', error_str, re.IGNORECASE)
                        if retry_match:
                            wait_time = max(wait_time, float(retry_match.group(1)) + 10)
                        else:
                            retry_delay_match = re.search(r"'retryDelay':\s*'(\d+)s'", error_str)
                            if retry_delay_match:
                                wait_time = max(wait_time, float(retry_delay_match.group(1)) + 10)
                    except:
                        pass
                    
                    print(f"⚠️ Rate limit hit (429), waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                # Nếu không phải lỗi quota hoặc đã retry hết, raise lỗi
                raise

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError:
            # Thử tìm đoạn JSON trong output (phòng khi model nói nhiều)
            start = raw_content.find("[")
            end = raw_content.rfind("]")
            if start == -1 or end == -1 or end <= start:
                return []
            try:
                data = json.loads(raw_content[start : end + 1])
            except json.JSONDecodeError:
                return []

        if not isinstance(data, list):
            return []

        claims: List[AgriClaim] = []
        for item in data:
            try:
                claim = AgriClaim(**item)
                claims.append(claim)
            except Exception:
                # Bỏ qua record sai định dạng
                continue

        return claims


def extract_claims_from_url(url: str) -> List[AgriClaim]:
    """
    Pipeline đầy đủ: URL -> scrape text -> Gemini -> List[AgriClaim].
    """
    if not url:
        return []

    result = scrape_clean_text(url)
    if not result.text.strip():
        return []

    claims = extract_claims_from_text(result.text)
    # Gắn source_url cho từng claim để dùng downstream (resolver, logging, ...)
    for c in claims:
        c.source_url = url
    return claims


__all__ = [
    "extract_claims_from_text",
    "extract_claims_from_url",
]

