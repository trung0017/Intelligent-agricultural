from __future__ import annotations

"""
Định nghĩa các model Pydantic dùng chung cho Agri-Agent.

Hiện tại bao gồm:
- AgriClaim: biểu diễn một khẳng định trích xuất từ văn bản nông nghiệp.
"""

from typing import Optional

from pydantic import BaseModel, Field


class AgriClaim(BaseModel):
    """
    Khai báo theo mẫu trong PROMPTS.md:

    {
      "subject": "Tên thực thể chính hóa (VD: Lúa ST25, Bệnh đạo ôn)",
      "predicate": "Thuộc tính (VD: Năng suất, Thời gian sinh trưởng, Khả năng chịu mặn)",
      "object": "Giá trị cụ thể bao gồm đơn vị (VD: 8.5 tấn/ha, 95-100 ngày)",
      "context": "Điều kiện áp dụng (VD: Vụ Đông Xuân, Vùng ven biển)",
      "confidence": "Độ tin cậy của mô hình (float 0.0 - 1.0)"
    }
    """

    subject: str = Field(
        ...,
        description="Tên thực thể chính hóa (VD: 'Lúa ST25', 'Bệnh đạo ôn').",
    )
    predicate: str = Field(
        ...,
        description="Thuộc tính/mối quan hệ (VD: 'Năng suất', 'Thời gian sinh trưởng').",
    )
    object: Optional[str] = Field(
        default=None,
        description=(
            "Giá trị cụ thể bao gồm đơn vị (VD: '8.5 tấn/ha', '95-100 ngày'). "
            "Nếu không tìm thấy thông tin định lượng, có thể là None."
        ),
    )
    context: Optional[str] = Field(
        default=None,
        description=(
            "Điều kiện áp dụng hoặc bối cảnh (VD: 'Vụ Đông Xuân', 'Vùng ven biển ĐBSCL')."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của mô hình (0.0 - 1.0).",
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL nơi claim được trích xuất (thêm cho downstream processing).",
    )


__all__ = ["AgriClaim"]

