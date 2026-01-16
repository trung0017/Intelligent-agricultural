from __future__ import annotations

"""
Web scraper nâng cao cho Agri-Agent.

Yêu cầu chính:
- Sử dụng `trafilatura` để lấy main text sạch.
- Dùng `charset_normalizer` để tự động phát hiện và decode các bảng mã cũ
  (Windows-1258, VNI, ...) thường gặp ở web nông nghiệp Việt Nam.
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from charset_normalizer import from_bytes
import trafilatura


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}


@dataclass
class ScrapeResult:
    """Kết quả scraping cơ bản."""

    url: str
    encoding: str
    raw_html: str
    text: str


def _normalize_url(url: str) -> str:
    """
    Chuẩn hóa URL:
    - Mã hóa phần path/query chứa ký tự Unicode (VD: dấu tiếng Việt, dấu gạch dài…)
    để tránh lỗi 'ascii codec' khi gọi urlopen.
    """
    url = url.strip()
    if not url:
        return url

    parts = urlsplit(url)
    path = quote(parts.path)
    query = quote(parts.query, safe="=&?")
    return urlunsplit((parts.scheme or "https", parts.netloc, path, query, parts.fragment))


def fetch_raw_bytes(url: str, timeout: int = 20) -> bytes:
    """
    Tải nội dung từ URL dưới dạng bytes (chưa decode).

    Sử dụng urllib trong stdlib để tránh phụ thuộc thêm thư viện HTTP.
    """
    normalized = _normalize_url(url)
    req = Request(normalized, headers=DEFAULT_HEADERS)
    with urlopen(req, timeout=timeout) as resp:  # type: ignore[union-attr]
        return resp.read()


def decode_with_charset_normalizer(data: bytes) -> tuple[str, str]:
    """
    Dùng charset_normalizer để tự phát hiện encoding và decode.

    Trả về (encoding, decoded_text).
    """
    if not data:
        return "utf-8", ""

    result = from_bytes(data).best()
    if result is None:
        # Fallback bảo thủ
        return "utf-8", data.decode("utf-8", errors="ignore")

    encoding = result.encoding or "utf-8"
    # str(result) trả về chuỗi đã decode với encoding phát hiện được
    text = str(result)
    return encoding, text


def extract_main_text(html: str, url: Optional[str] = None) -> str:
    """
    Trích xuất main text từ HTML.

    - Ưu tiên dùng trafilatura (tối ưu cho bài báo/tin tức).
    - Nếu thất bại, fallback sang BeautifulSoup.get_text().
    """
    if not html.strip():
        return ""

    # Trafilatura: cho kết quả sạch, bỏ menu, sidebar, quảng cáo...
    try:
        extracted = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
        )
    except Exception:
        extracted = None

    if extracted:
        extracted = extracted.strip()
        if extracted:
            return extracted

    # Fallback: lấy toàn bộ text từ HTML
    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        return "\n".join(
            line.strip() for line in text.splitlines() if line.strip()
        )
    except Exception:
        return ""


def scrape_clean_text(url: str, timeout: int = 20) -> ScrapeResult:
    """
    Pipeline đầy đủ:
    1) Thử dùng trafilatura.fetch_url (có sẵn logic HTTP & decode).
    2) Nếu thất bại, fallback:
       - Download HTML (bytes)
       - Phát hiện encoding bằng charset_normalizer
       - Decode sang Unicode
    3) Extract main text bằng trafilatura (có fallback BeautifulSoup)
    """
    html: str
    encoding: str = "utf-8"

    # Bước 1: ưu tiên fetch_url của trafilatura (đã xử lý khá tốt redirect, encoding...)
    try:
        downloaded = trafilatura.fetch_url(url)
    except Exception:
        downloaded = None

    if downloaded:
        # fetch_url trả về string HTML đã decode
        html = downloaded
    else:
        # Bước 2: fallback sang urllib + charset_normalizer
        raw_bytes = fetch_raw_bytes(url, timeout=timeout)
        encoding, html = decode_with_charset_normalizer(raw_bytes)

    text = extract_main_text(html, url=url)
    return ScrapeResult(url=url, encoding=encoding, raw_html=html, text=text)


__all__ = [
    "ScrapeResult",
    "fetch_raw_bytes",
    "decode_with_charset_normalizer",
    "extract_main_text",
    "scrape_clean_text",
]

