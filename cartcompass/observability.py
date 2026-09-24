"""OpenTelemetry-compatible Observability, Distributed Tracing, and Metrics Engine."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
import datetime
import json
import logging
import time
from typing import Any, Callable, Generator
import uuid


logger = logging.getLogger("grocery_optimizer.telemetry")
if not logger.handlers:
  handler = logging.StreamHandler()
  handler.setFormatter(
      logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
  )
  logger.addHandler(handler)
  logger.setLevel(logging.INFO)


@dataclass
class SpanEvent:
  name: str
  timestamp_iso: str
  attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
  trace_id: str
  span_id: str
  parent_span_id: str | None
  operation_name: str
  start_time_iso: str
  start_perf_ns: int
  end_perf_ns: int = 0
  duration_ms: float = 0.0
  status: str = "UNSET"  # "OK", "ERROR", "UNSET"
  attributes: dict[str, Any] = field(default_factory=dict)
  events: list[SpanEvent] = field(default_factory=list)
  error_message: str | None = None

  def set_attribute(self, key: str, value: Any) -> None:
    self.attributes[key] = value

  def add_event(self, name: str, **kwargs: Any) -> None:
    self.events.append(
        SpanEvent(
            name=name,
            timestamp_iso=datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            attributes=kwargs,
        )
    )

  def finish(self, status: str = "OK", error_message: str | None = None) -> None:
    self.end_perf_ns = time.perf_counter_ns()
    self.duration_ms = round((self.end_perf_ns - self.start_perf_ns) / 1e6, 3)
    self.status = status
    self.error_message = error_message

  def to_dict(self) -> dict[str, Any]:
    data = asdict(self)
    data.pop("start_perf_ns", None)
    data.pop("end_perf_ns", None)
    return data


class MetricsRegistry:
  """In-memory Prometheus/OpenTelemetry-compatible metrics registry."""

  def __init__(self) -> None:
    self.counters: dict[str, float] = {}
    self.gauges: dict[str, float] = {}
    self.histograms: dict[str, list[float]] = {}

  def inc_counter(self, name: str, value: float = 1.0) -> None:
    self.counters[name] = self.counters.get(name, 0.0) + value

  def set_gauge(self, name: str, value: float) -> None:
    self.gauges[name] = value

  def observe_histogram(self, name: str, value: float) -> None:
    self.histograms.setdefault(name, []).append(round(value, 3))

  def snapshot(self) -> dict[str, Any]:
    hist_summary = {}
    for k, values in self.histograms.items():
      if values:
        sorted_vals = sorted(values)
        p95_idx = min(len(sorted_vals) - 1, int(len(sorted_vals) * 0.95))
        hist_summary[k] = {
            "count": len(values),
            "min": sorted_vals[0],
            "avg": round(sum(values) / len(values), 3),
            "p95": sorted_vals[p95_idx],
            "max": sorted_vals[-1],
        }
    return {
        "counters": dict(self.counters),
        "gauges": dict(self.gauges),
        "histograms": hist_summary,
    }


class TraceRecorder:
  """Manages distributed trace spans and structured audit logs for an execution run."""

  def __init__(self, trace_id: str | None = None) -> None:
    self.trace_id: str = trace_id or uuid.uuid4().hex
    self.spans: list[Span] = []
    self._active_span_stack: list[Span] = []
    self.metrics = MetricsRegistry()

  @property
  def current_span(self) -> Span | None:
    return self._active_span_stack[-1] if self._active_span_stack else None

  @contextmanager
  def start_span(
      self, operation_name: str, **initial_attributes: Any
  ) -> Generator[Span, None, None]:
    parent_id = self.current_span.span_id if self.current_span else None
    span = Span(
        trace_id=self.trace_id,
        span_id=uuid.uuid4().hex[:16],
        parent_span_id=parent_id,
        operation_name=operation_name,
        start_time_iso=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        start_perf_ns=time.perf_counter_ns(),
        attributes=dict(initial_attributes),
    )
    self.spans.append(span)
    self._active_span_stack.append(span)
    try:
      yield span
      span.finish(status="OK")
    except Exception as exc:
      span.finish(status="ERROR", error_message=str(exc))
      self.metrics.inc_counter(f"errors.{operation_name}", 1.0)
      logger.error(
          json.dumps({
              "event": "span_error",
              "trace_id": self.trace_id,
              "span_id": span.span_id,
              "operation": operation_name,
              "error": str(exc),
          })
      )
      raise
    finally:
      self._active_span_stack.pop()
      self.metrics.observe_histogram(
          f"latency_ms.{operation_name}", span.duration_ms
      )

  def export_trace_summary(self) -> dict[str, Any]:
    total_duration = (
        self.spans[0].duration_ms
        if self.spans
        else sum(s.duration_ms for s in self.spans)
    )
    return {
        "trace_id": self.trace_id,
        "total_spans": len(self.spans),
        "root_duration_ms": round(total_duration, 3),
        "error_count": sum(1 for s in self.spans if s.status == "ERROR"),
        "spans": [s.to_dict() for s in self.spans],
        "metrics": self.metrics.snapshot(),
    }
