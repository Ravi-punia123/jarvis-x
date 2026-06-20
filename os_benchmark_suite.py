"""Automatic Performance Benchmark suite measuring startup, inference, and response latency."""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
from logger import get_logger

_log = get_logger("os_benchmarks")


class OSBenchmarkSuite:
    """Measures startup, inference, memory search, and tool execution latency."""

    def __init__(self, history_path: str = "benchmark_history.json"):
        self.history_path = Path(history_path)
        self._benchmarks: Dict[str, List[float]] = {}
        self._load()

    def _load(self) -> None:
        if self.history_path.exists():
            try:
                self._benchmarks = json.loads(self.history_path.read_text(encoding="utf-8"))
            except Exception:
                self._benchmarks = {}

    def save(self) -> None:
        try:
            self.history_path.write_text(json.dumps(self._benchmarks, indent=2), encoding="utf-8")
        except Exception as e:
            _log.error("Failed to write benchmark logs: %s", str(e))

    def record(self, metric: str, duration_sec: float) -> None:
        if metric not in self._benchmarks:
            self._benchmarks[metric] = []
        self._benchmarks[metric].append(round(duration_sec, 4))
        # Keep last 50 historical points per metric
        self._benchmarks[metric] = self._benchmarks[metric][-50:]
        self.save()

    def get_averages(self) -> Dict[str, float]:
        averages: Dict[str, float] = {}
        for metric, points in self._benchmarks.items():
            if points:
                averages[metric] = round(sum(points) / len(points), 4)
        return averages
