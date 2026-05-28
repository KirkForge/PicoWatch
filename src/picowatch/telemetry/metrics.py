"""L7 Telemetry — Prometheus metrics (zero-dep rendering).

Prometheus text-format metrics exposed on admin port.
"""

from __future__ import annotations


class PrometheusMetrics:
    """Zero-dependency Prometheus metrics renderer.

    Collects counters and histograms for PicoWatch scans.
    """

    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def inc_counter(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        self._gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe a value for a histogram metric."""
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)

    def render(self) -> str:
        """Render all metrics in Prometheus text format."""
        lines: list[str] = []

        # Counters
        for key, value in sorted(self._counters.items()):
            name, labels = self._parse_key(key)
            lines.append(f"# HELP {name} {name}")
            lines.append(f"# TYPE {name} counter")
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f"{name}{{{label_str}}} {value}")
            else:
                lines.append(f"{name} {value}")

        # Gauges
        for key, value in sorted(self._gauges.items()):
            name, labels = self._parse_key(key)
            lines.append(f"# HELP {name} {name}")
            lines.append(f"# TYPE {name} gauge")
            if labels:
                label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                lines.append(f"{name}{{{label_str}}} {value}")
            else:
                lines.append(f"{name} {value}")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _make_key(name: str, labels: dict[str, str] | None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    @staticmethod
    def _parse_key(key: str) -> tuple[str, dict[str, str] | None]:
        if "{" not in key:
            return key, None
        name = key.split("{")[0]
        label_str = key.split("{")[1].rstrip("}")
        labels = {}
        for pair in label_str.split(","):
            k, v = pair.split("=", 1)
            labels[k] = v
        return name, labels
