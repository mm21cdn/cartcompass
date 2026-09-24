"""OpenTelemetry-compatible Observability, Distributed Tracing, Structured JSON Logging, and PII Redaction Engine."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
import datetime
import json
import logging
import re
import time
from typing import Any, Generator
import uuid


class PIIRedactor:
  """Redacts Personal Identifiable Information (PII) & secrets from logs, traces, and SQLite memory."""

  _EMAIL_RE = re.compile(
      r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
  )
  _UK_PHONE_RE = re.compile(
      r"(?:(?:\+44\s?\(0\)\s?|\+44\s?|0)(?:7\d{3}|\d{3,4})\s?\d{3}\s?\d{3,4})\b"
  )
  _CARD_PAN_RE = re.compile(
      r"\b(?:\d[ -]*?){13,19}\b"
  )
  _UK_NI_RE = re.compile(
      r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b",
      re.IGNORECASE,
  )
  _STREET_ADDR_RE = re.compile(
      r"\b(?:Flat\s+\d+[A-Za-z]?,\s*)?\d{1,4}\s+[A-Z][a-zA-Z]+\s+(?:Street|St|Road|Rd|Lane|Ln|Avenue|Ave|Close|Way|Drive|Dr|Gardens|Court)\b",
      re.IGNORECASE,
  )
  _API_KEY_RE = re.compile(
      r"\b(?:AIza[0-9A-Za-z\-_]{20,}|sk-[0-9A-Za-z]{20,}|Bearer\s+[0-9A-Za-z\-_\.]{16,})\b"
  )

  SENSITIVE_KEYS = frozenset({
      "email",
      "phone",
      "phone_number",
      "mobile",
      "credit_card",
      "card_number",
      "loyalty_card_number",
      "clubcard_number",
      "nectar_card_number",
      "ni_number",
      "password",
      "api_key",
      "secret",
      "token",
      "authorization",
      "street_address",
  })

  def __init__(self) -> None:
    self.redaction_counts: dict[str, int] = {
        "email": 0,
        "uk_phone": 0,
        "card_number": 0,
        "uk_ni": 0,
        "street_address": 0,
        "secret_token": 0,
        "sensitive_key": 0,
    }

  def redact_text(self, text: str) -> str:
    """Scans and masks PII patterns in arbitrary free-form text."""
    if not text or not isinstance(text, str):
      return text

    out = text
    out, n_sec = self._API_KEY_RE.subn("[REDACTED_SECRET]", out)
    self.redaction_counts["secret_token"] += n_sec

    out, n_email = self._EMAIL_RE.subn("[REDACTED_EMAIL]", out)
    self.redaction_counts["email"] += n_email

    out, n_ni = self._UK_NI_RE.subn("[REDACTED_UK_NI]", out)
    self.redaction_counts["uk_ni"] += n_ni

    out, n_card = self._CARD_PAN_RE.subn("[REDACTED_CARD_NUMBER]", out)
    self.redaction_counts["card_number"] += n_card

    out, n_phone = self._UK_PHONE_RE.subn("[REDACTED_UK_PHONE]", out)
    self.redaction_counts["uk_phone"] += n_phone

    out, n_addr = self._STREET_ADDR_RE.subn("[REDACTED_STREET_ADDRESS]", out)
    self.redaction_counts["street_address"] += n_addr

    return out

  def mask_coordinate_for_log(self, coord_val: float) -> str:
    """Masks exact GPS coordinates to ~1km coarse precision for external logs."""
    return f"{coord_val:.2f}***"

  def redact_payload(self, obj: Any, mask_gps_in_logs: bool = False) -> Any:
    """Recursively redacts PII across dictionaries, lists, and strings."""
    if isinstance(obj, str):
      return self.redact_text(obj)
    if isinstance(obj, list):
      return [self.redact_payload(item, mask_gps_in_logs=mask_gps_in_logs) for item in obj]
    if isinstance(obj, tuple):
      return tuple(self.redact_payload(item, mask_gps_in_logs=mask_gps_in_logs) for item in obj)
    if isinstance(obj, dict):
      sanitized: dict[str, Any] = {}
      for k, v in obj.items():
        key_low = str(k).lower()
        if key_low in self.SENSITIVE_KEYS:
          self.redaction_counts["sensitive_key"] += 1
          sanitized[k] = "[REDACTED_SENSITIVE_FIELD]"
        elif mask_gps_in_logs and key_low in ("latitude", "longitude", "home_latitude", "home_longitude") and isinstance(v, (int, float)):
          sanitized[k] = self.mask_coordinate_for_log(float(v))
        else:
          sanitized[k] = self.redact_payload(v, mask_gps_in_logs=mask_gps_in_logs)
      return sanitized
    return obj

  @property
  def total_redactions(self) -> int:
    return sum(self.redaction_counts.values())


GLOBAL_PII_REDACTOR = PIIRedactor()


class StructuredJsonFormatter(logging.Formatter):
  """Formats Python LogRecords as Google Cloud Logging / OpenTelemetry structured JSON."""

  def format(self, record: logging.LogRecord) -> str:
    structured_payload = getattr(record, "structured_data", None)
    if isinstance(structured_payload, dict):
      base = dict(structured_payload)
    else:
      base = {"message": record.getMessage()}

    envelope = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "severity": record.levelname,
        "service": "cartcompass-uk-agent",
        "logger": record.name,
        "pii_redacted": True,
        **GLOBAL_PII_REDACTOR.redact_payload(base, mask_gps_in_logs=True),
    }
    return json.dumps(envelope, sort_keys=True)


class StructuredJsonLogger:
  """Structured JSON logger with automatic PII redaction and in-memory queryable log buffer."""

  def __init__(
      self,
      name: str = "grocery_optimizer.telemetry",
      redactor: PIIRedactor | None = None,
      max_buffer_entries: int = 500,
  ) -> None:
    self.redactor = redactor or GLOBAL_PII_REDACTOR
    self.max_buffer_entries = max_buffer_entries
    self.records: list[dict[str, Any]] = []
    self._logger = logging.getLogger(name)
    if not self._logger.handlers:
      handler = logging.StreamHandler()
      handler.setFormatter(StructuredJsonFormatter())
      self._logger.addHandler(handler)
      self._logger.setLevel(logging.INFO)

  def log_event(
      self,
      event_type: str,
      *,
      severity: str = "INFO",
      trace_id: str | None = None,
      span_id: str | None = None,
      parent_span_id: str | None = None,
      operation_name: str | None = None,
      agent_name: str | None = None,
      model_id: str | None = None,
      intent: str | None = None,
      outcome: str | None = None,
      duration_ms: float | None = None,
      attributes: dict[str, Any] | None = None,
  ) -> dict[str, Any]:
    raw_entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "severity": severity.upper(),
        "service": "cartcompass-uk-agent",
        "event_type": event_type,
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "operation_name": operation_name,
        "agent_name": agent_name,
        "model_id": model_id,
        "intent": intent,
        "outcome": outcome,
        "duration_ms": duration_ms,
        "pii_redacted": True,
        "attributes": attributes or {},
    }
    sanitized_entry = self.redactor.redact_payload(
        raw_entry, mask_gps_in_logs=True
    )
    if len(self.records) >= self.max_buffer_entries:
      self.records.pop(0)
    self.records.append(sanitized_entry)

    level = getattr(logging, severity.upper(), logging.INFO)
    self._logger.log(
        level,
        json.dumps(sanitized_entry),
        extra={"structured_data": sanitized_entry},
    )
    return sanitized_entry


STRUCTURED_LOGGER = StructuredJsonLogger()
logger = STRUCTURED_LOGGER._logger


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
    self.attributes[key] = GLOBAL_PII_REDACTOR.redact_payload(value)

  def add_event(self, name: str, **kwargs: Any) -> None:
    self.events.append(
        SpanEvent(
            name=name,
            timestamp_iso=datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
            attributes=GLOBAL_PII_REDACTOR.redact_payload(kwargs),
        )
    )

  def finish(self, status: str = "OK", error_message: str | None = None) -> None:
    self.end_perf_ns = time.perf_counter_ns()
    self.duration_ms = round((self.end_perf_ns - self.start_perf_ns) / 1e6, 3)
    self.status = status
    self.error_message = (
        GLOBAL_PII_REDACTOR.redact_text(error_message)
        if error_message
        else None
    )

  def to_dict(self) -> dict[str, Any]:
    data = asdict(self)
    data.pop("start_perf_ns", None)
    data.pop("end_perf_ns", None)
    return GLOBAL_PII_REDACTOR.redact_payload(data)


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
        "pii_redaction_counts": dict(GLOBAL_PII_REDACTOR.redaction_counts),
    }


class TraceRecorder:
  """Manages distributed trace spans, structured JSON logs, and PII redaction for an agent run."""

  def __init__(
      self,
      trace_id: str | None = None,
      structured_logger: StructuredJsonLogger | None = None,
      pii_redactor: PIIRedactor | None = None,
  ) -> None:
    self.trace_id: str = trace_id or uuid.uuid4().hex
    self.spans: list[Span] = []
    self._active_span_stack: list[Span] = []
    self.metrics = MetricsRegistry()
    self.structured_logger = structured_logger or STRUCTURED_LOGGER
    self.pii_redactor = pii_redactor or GLOBAL_PII_REDACTOR
    self.structured_logs: list[dict[str, Any]] = []

  @property
  def current_span(self) -> Span | None:
    return self._active_span_stack[-1] if self._active_span_stack else None

  def log_structured(
      self,
      event_type: str,
      *,
      severity: str = "INFO",
      agent_name: str | None = None,
      model_id: str | None = None,
      intent: str | None = None,
      outcome: str | None = None,
      attributes: dict[str, Any] | None = None,
  ) -> dict[str, Any]:
    active = self.current_span
    record = self.structured_logger.log_event(
        event_type,
        severity=severity,
        trace_id=self.trace_id,
        span_id=active.span_id if active else None,
        parent_span_id=active.parent_span_id if active else None,
        operation_name=active.operation_name if active else None,
        agent_name=agent_name,
        model_id=model_id,
        intent=intent,
        outcome=outcome,
        duration_ms=active.duration_ms if active else None,
        attributes=attributes,
    )
    self.structured_logs.append(record)
    return record

  @contextmanager
  def start_span(
      self, operation_name: str, **initial_attributes: Any
  ) -> Generator[Span, None, None]:
    parent_id = self.current_span.span_id if self.current_span else None
    redacted_attrs = self.pii_redactor.redact_payload(dict(initial_attributes))
    span = Span(
        trace_id=self.trace_id,
        span_id=uuid.uuid4().hex[:16],
        parent_span_id=parent_id,
        operation_name=operation_name,
        start_time_iso=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        start_perf_ns=time.perf_counter_ns(),
        attributes=redacted_attrs,
    )
    self.spans.append(span)
    self._active_span_stack.append(span)
    self.log_structured(
        "span_started",
        severity="INFO",
        agent_name=str(redacted_attrs.get("agent_name", "CartCompassOrchestrator")),
        model_id=str(redacted_attrs.get("model_id", "deterministic+gemini-router")),
        intent=f"Execute {operation_name}",
        outcome="IN_PROGRESS",
        attributes=redacted_attrs,
    )
    try:
      yield span
      span.finish(status="OK")
      self.log_structured(
          "span_completed",
          severity="INFO",
          agent_name=str(span.attributes.get("agent_name", "CartCompassOrchestrator")),
          model_id=str(span.attributes.get("model_id", "deterministic+gemini-router")),
          intent=f"Complete {operation_name}",
          outcome="SUCCESS",
          attributes={"duration_ms": span.duration_ms, **span.attributes},
      )
    except Exception as exc:
      span.finish(status="ERROR", error_message=str(exc))
      self.metrics.inc_counter(f"errors.{operation_name}", 1.0)
      self.log_structured(
          "span_error",
          severity="ERROR",
          agent_name=str(span.attributes.get("agent_name", "CartCompassOrchestrator")),
          intent=f"Execute {operation_name}",
          outcome="ERROR",
          attributes={
              "error": self.pii_redactor.redact_text(str(exc)),
              "duration_ms": span.duration_ms,
          },
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
        "pii_redactions_applied": self.pii_redactor.total_redactions,
        "structured_log_count": len(self.structured_logs),
        "structured_logs": self.structured_logs[-25:],
        "spans": [s.to_dict() for s in self.spans],
        "metrics": self.metrics.snapshot(),
    }
