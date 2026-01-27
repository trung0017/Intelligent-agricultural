"""
Rate Limiter và Circuit Breaker để tránh vượt rate limit API.

Tính năng:
- Rate Limiter: Giới hạn số requests mỗi giây
- Circuit Breaker: Tự động dừng khi có quá nhiều lỗi 429
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    """Trạng thái của Circuit Breaker."""
    CLOSED = "closed"  # Bình thường, cho phép requests
    OPEN = "open"  # Đã mở, từ chối tất cả requests
    HALF_OPEN = "half_open"  # Đang thử nghiệm, cho phép một số requests


@dataclass
class RateLimiter:
    """
    Rate Limiter: Giới hạn số requests trong một khoảng thời gian.
    
    Ví dụ: max_requests=10, time_window=1.0 → Tối đa 10 requests/giây
    """
    
    max_requests: int = 10
    time_window: float = 1.0  # giây
    _requests: deque = None
    
    def __post_init__(self):
        if self._requests is None:
            self._requests = deque()
    
    def wait_if_needed(self) -> None:
        """
        Chờ nếu cần thiết để tuân thủ rate limit.
        """
        now = time.time()
        
        # Xóa các requests cũ hơn time_window
        while self._requests and self._requests[0] < now - self.time_window:
            self._requests.popleft()
        
        # Nếu đã đạt max, chờ
        if len(self._requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self._requests[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
                # Xóa lại sau khi chờ
                now = time.time()
                while self._requests and self._requests[0] < now - self.time_window:
                    self._requests.popleft()
        
        self._requests.append(time.time())


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker: Tự động dừng requests khi có quá nhiều lỗi.
    
    Logic:
    - CLOSED: Bình thường, cho phép requests
    - OPEN: Khi số lỗi 429 >= failure_threshold, từ chối tất cả requests
    - HALF_OPEN: Sau timeout, thử một số requests để kiểm tra
    """
    
    failure_threshold: int = 5  # Số lỗi 429 để mở circuit
    timeout: float = 60.0  # Thời gian chờ trước khi chuyển sang HALF_OPEN (giây)
    half_open_max_requests: int = 3  # Số requests cho phép trong HALF_OPEN
    
    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _last_failure_time: Optional[float] = None
    _half_open_requests: int = 0
    _half_open_success_count: int = 0
    
    def can_make_request(self) -> bool:
        """
        Kiểm tra xem có thể thực hiện request không.
        
        Returns:
            True nếu có thể, False nếu bị chặn
        """
        now = time.time()
        
        # Nếu đang OPEN, kiểm tra xem đã hết timeout chưa
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and (now - self._last_failure_time) >= self.timeout:
                # Chuyển sang HALF_OPEN để thử nghiệm
                self._state = CircuitState.HALF_OPEN
                self._half_open_requests = 0
                self._half_open_success_count = 0
                return True
            return False
        
        # Nếu đang HALF_OPEN, giới hạn số requests
        if self._state == CircuitState.HALF_OPEN:
            if self._half_open_requests >= self.half_open_max_requests:
                return False
            return True
        
        # CLOSED: Cho phép
        return True
    
    def record_success(self) -> None:
        """Ghi nhận request thành công."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_success_count += 1
            # Nếu tất cả requests trong HALF_OPEN thành công, đóng circuit
            if self._half_open_success_count >= self.half_open_max_requests:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._half_open_requests = 0
                self._half_open_success_count = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count khi có success
            self._failure_count = 0
    
    def record_failure(self, is_429: bool = False) -> None:
        """
        Ghi nhận request thất bại.
        
        Args:
            is_429: True nếu là lỗi 429 (rate limit)
        """
        if is_429:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            # Nếu đạt threshold, mở circuit
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                print(f"🚨 Circuit Breaker OPEN: {self._failure_count} lỗi 429 liên tiếp")
        
        if self._state == CircuitState.HALF_OPEN:
            # Nếu có lỗi trong HALF_OPEN, mở lại circuit
            self._state = CircuitState.OPEN
            self._last_failure_time = time.time()
    
    def record_request(self) -> None:
        """Ghi nhận đã thực hiện một request (cho HALF_OPEN)."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_requests += 1
    
    def get_state(self) -> CircuitState:
        """Lấy trạng thái hiện tại."""
        return self._state
    
    def reset(self) -> None:
        """Reset circuit breaker về trạng thái ban đầu."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_requests = 0
        self._half_open_success_count = 0


# Global instances
_global_rate_limiter = RateLimiter(max_requests=8, time_window=1.0)  # 8 requests/giây
_global_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=120.0)  # 3 lỗi 429 → mở circuit, chờ 2 phút


def get_rate_limiter() -> RateLimiter:
    """Lấy global rate limiter."""
    return _global_rate_limiter


def get_circuit_breaker() -> CircuitBreaker:
    """Lấy global circuit breaker."""
    return _global_circuit_breaker


__all__ = [
    "RateLimiter",
    "CircuitBreaker",
    "CircuitState",
    "get_rate_limiter",
    "get_circuit_breaker",
]
