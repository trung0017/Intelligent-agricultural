from __future__ import annotations

"""
Domain filter cho Agri-Agent.

Nhiệm vụ chính: cho điểm độ tin cậy (trust score) của URL theo loại domain.

Quy tắc (theo PROMPTS.md):
- Domain .gov.vn  -> 1.0 điểm
- Domain .edu.vn  -> 0.9 điểm
- Báo chí chính thống -> 0.8 điểm
- Khác -> 0.5 điểm
"""

from urllib.parse import urlparse


# Một số domain báo chí chính thống phổ biến ở Việt Nam.
OFFICIAL_NEWS_DOMAINS: dict[str, float] = {
    "vnexpress.net": 0.8,
    "tuoitre.vn": 0.8,
    "thanhnien.vn": 0.8,
    "nld.com.vn": 0.8,
    "dantri.com.vn": 0.8,
    "vietnamplus.vn": 0.8,
    "vtv.vn": 0.8,
    "vov.vn": 0.8,
    "baochinhphu.vn": 0.8,
    "nongnghiep.vn": 0.8,
}


def _get_hostname(url: str) -> str:
    """Chuẩn hóa và lấy hostname từ URL."""
    parsed = urlparse(url.strip())
    host = parsed.netloc or parsed.path  # phòng trường hợp thiếu scheme
    # Bỏ port nếu có (vd: example.com:8080)
    if ":" in host:
        host = host.split(":", 1)[0]
    return host.lower()


def calculate_trust_score(url: str) -> float:
    """
    Tính điểm độ tin cậy của URL theo loại domain.

    Parameters
    ----------
    url: str
        Đường dẫn nguồn tin.

    Returns
    -------
    float
        Điểm tin cậy trong khoảng [0.0, 1.0].
    """
    if not url:
        return 0.5

    host = _get_hostname(url)

    # Cơ quan nhà nước Việt Nam
    if host.endswith(".gov.vn"):
        return 1.0

    # Tổ chức giáo dục Việt Nam
    if host.endswith(".edu.vn"):
        return 0.9

    # Báo chí chính thống
    if host in OFFICIAL_NEWS_DOMAINS:
        return OFFICIAL_NEWS_DOMAINS[host]

    # Mặc định
    return 0.5


__all__ = ["calculate_trust_score", "OFFICIAL_NEWS_DOMAINS"]

