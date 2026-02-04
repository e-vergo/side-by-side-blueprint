"""Wall-clock timing utilities for SBS workflows."""

import time
from typing import Optional


class TimingContext:
    """Context manager that records wall-clock duration into a dict.

    Usage:
        timings = {}
        with TimingContext(timings, "extraction"):
            do_work()
        # timings["extraction"] == 1.234
    """

    def __init__(self, timings: dict[str, float], key: str) -> None:
        self.timings = timings
        self.key = key
        self._start: Optional[float] = None

    def __enter__(self) -> "TimingContext":
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._start is not None:
            self.timings[self.key] = round(time.monotonic() - self._start, 3)
        return None  # Don't suppress exceptions


def format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration.

    Examples:
        0.5 -> "0.5s"
        65.3 -> "1m 5.3s"
        3661.0 -> "1h 1m 1.0s"
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remaining:.1f}s"

    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m {remaining:.1f}s"


def timing_summary(timings: dict[str, float]) -> str:
    """Format a timings dict as a summary string.

    Example output:
        extraction: 2.1s | tagging: 0.3s | porcelain: 12.4s | total: 14.8s
    """
    if not timings:
        return "(no timing data)"

    parts = [f"{k}: {format_duration(v)}" for k, v in timings.items()]
    total = sum(timings.values())
    parts.append(f"total: {format_duration(total)}")
    return " | ".join(parts)
