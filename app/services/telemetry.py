import time
from collections import defaultdict
from typing import Dict, Tuple


class TelemetryCollector:
    """Singleton in-process metrics accumulator for Prometheus exposition."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.start_time = time.time()
            cls._instance.request_counts: Dict[Tuple[str, str, int], int] = defaultdict(int)
            cls._instance.request_duration_sum = 0.0
            cls._instance.request_duration_count = 0
            cls._instance.error_counts: Dict[int, int] = defaultdict(int)
        return cls._instance

    def record_request(self, method: str, path: str, status_code: int, duration_seconds: float) -> None:
        normalized_path = self._normalize_path(path)
        self.request_counts[(method, normalized_path, status_code)] += 1
        self.request_duration_sum += duration_seconds
        self.request_duration_count += 1
        if status_code >= 400:
            self.error_counts[status_code] += 1

    def _normalize_path(self, path: str) -> str:
        if not path:
            return "/"
        if path.startswith("/static"):
            return "/static"
        if path.startswith("/api/projects/"):
            return "/api/projects/{id}"
        if path.startswith("/api/papers/"):
            return "/api/papers/{id}"
        if path.startswith("/api/documents/"):
            return "/api/documents/{id}"
        if path.startswith("/api/notes/"):
            return "/api/notes/{id}"
        return path

    def get_uptime_seconds(self) -> float:
        return time.time() - self.start_time

    def get_request_counts(self) -> Dict[Tuple[str, str, int], int]:
        return dict(self.request_counts)

    def get_error_counts(self) -> Dict[int, int]:
        return dict(self.error_counts)


telemetry = TelemetryCollector()
