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

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.models import AgriClaim
from src.tools.scraper import scrape_clean_text


EXTRACTION_SYSTEM_PROMPT = (
    "Bạn là Chuyên gia Dữ liệu Nông nghiệp Việt Nam.\n"
    "Nhiệm vụ: Trích xuất các khẳng định (Claims) từ văn bản về giống cây trồng/"
    "kỹ thuật canh tác.\n\n"
    "Yêu cầu Output: trả về một JSON array các object theo schema AgriClaim:\n"
    "{\n"
    '  "subject": "Tên thực thể chính hóa (VD: Lúa ST25, Bệnh đạo ôn)",\n'
    '  "predicate": "Thuộc tính (VD: Năng suất, Thời gian sinh trưởng, Khả năng chịu mặn)",\n'
    '  "object": "Giá trị cụ thể bao gồm đơn vị (VD: 8.5 tấn/ha, 95-100 ngày) hoặc null nếu không có",\n'
    '  "context": "Điều kiện áp dụng (VD: Vụ Đông Xuân, Vùng ven biển) hoặc null",\n'
    '  "confidence": "Độ tin cậy của mô hình (float 0.0 - 1.0)"\n'
    "}\n\n"
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
    #   * gemini-2.5-flash: Model mới nhất, nhanh và hiệu quả
    #   * gemini-flash-latest: Alias luôn trỏ tới model flash mới nhất
    #   * gemini-2.5-flash-lite: Phiên bản nhẹ hơn
    # - Sử dụng "gemini-flash-latest" để luôn dùng model mới nhất, hoặc "gemini-2.5-flash" cho version cụ thể
    return ChatGoogleGenerativeAI(
        model="gemini-flash-latest",  # Luôn dùng model flash mới nhất
        api_key=api_key,
        temperature=0.2,
    )


def extract_claims_from_text(text: str) -> List[AgriClaim]:
    """
    Trích xuất danh sách AgriClaim từ đoạn văn bản tiếng Việt liên quan nông nghiệp.
    """
    text = (text or "").strip()
    if not text:
        return []

    client = _get_gemini_client()

    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=f"Input Text:\n{text}"),
    ]

    response = client.invoke(messages)
    raw_content = response.content if isinstance(response.content, str) else (
        "".join(part["text"] for part in response.content if isinstance(part, dict) and "text" in part)
        if isinstance(response.content, Iterable)
        else str(response.content)
    )

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

