"""Rate limiting middleware for PicoWatch HTTP server.

Per-IP sliding window rate limiter using only stdlib.
Configurable requests-per-window with configurable window size.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RateLimitEntry:
    """Track request timestamps for a single client IP."""

    timestamps: list[float] = field(default_factory=list)


class RateLimiter:
    """Sliding window rate limiter.

    Tracks per-IP request counts within a configurable time window.
    Deterministic within a single process — same IP, same window, same result.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

    def is_allowed(self, client_ip: str) -> bool:
        """Check if a request from client_ip is within rate limits.

        Uses sliding window: removes timestamps older than window_seconds,
        then checks if the count is within limits.
        """
        now = time.monotonic()
        entry = self._clients[client_ip]
        cutoff = now - self.window_seconds

        # Prune old timestamps
        entry.timestamps = [ts for ts in entry.timestamps if ts > cutoff]

        if len(entry.timestamps) >= self.max_requests:
            return False

        entry.timestamps.append(now)
        return True

    def reset(self, client_ip: str | None = None) -> None:
        """Reset rate limit state for a specific IP or all IPs."""
        if client_ip:
            self._clients.pop(client_ip, None)
        else:
            self._clients.clear()

    @property
    def active_clients(self) -> int:
        """Number of clients currently tracked."""
        return len(self._clients)
