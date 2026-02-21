import statistics
from typing import Any

from app.config import settings


class PredictiveAnomalyDetectionService:
    def analyze(
        self,
        *,
        events: list[dict[str, Any]],
        queue_snapshots: list[dict[str, Any]],
        start_ts: float,
        end_ts: float,
        bucket_minutes: int,
        min_events: int,
    ) -> dict[str, Any]:
        bucket_seconds = max(60, int(bucket_minutes) * 60)
        window_events = self._normalize_events(events=events, start_ts=start_ts, end_ts=end_ts)
        queue_summary = self._summarize_queues(queue_snapshots)

        if len(window_events) < max(5, int(min_events)):
            risk_from_backlog = self._backlog_risk(queue_summary["total_messages"])
            return {
                "status": "insufficient_data",
                "window": {
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "bucket_minutes": int(bucket_minutes),
                    "total_events": len(window_events),
                },
                "current": {
                    "latency_p95_ms": None,
                    "error_rate": None,
                    "queue_backlog_total": int(queue_summary["total_messages"]),
                },
                "forecast": {},
                "anomalies": (
                    [
                        {
                            "metric": "queue_backlog_total",
                            "severity": "medium" if risk_from_backlog >= 40 else "low",
                            "current": int(queue_summary["total_messages"]),
                            "baseline": int(
                                getattr(settings, "AI_ANOMALY_BACKLOG_THRESHOLD", 200) or 200
                            ),
                            "reason": "backlog acima do limite configurado",
                            "recommendation": "avaliar consumo das filas e workers ativos",
                        }
                    ]
                    if risk_from_backlog > 0
                    else []
                ),
                "queue_backlog": queue_summary["queues"],
                "risk": {
                    "score": int(risk_from_backlog),
                    "level": self._risk_level(risk_from_backlog),
                    "should_alert": risk_from_backlog >= 40,
                    "reasons": ["insufficient_event_volume_for_timeseries_model"],
                },
            }

        buckets = self._build_buckets(
            events=window_events,
            start_ts=start_ts,
            end_ts=end_ts,
            bucket_seconds=bucket_seconds,
        )
        series = self._extract_series(buckets)
        if not series["latency_p95_ms"] or not series["error_rate"]:
            return {
                "status": "insufficient_data",
                "window": {
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "bucket_minutes": int(bucket_minutes),
                    "total_events": len(window_events),
                },
                "current": {
                    "latency_p95_ms": None,
                    "error_rate": None,
                    "queue_backlog_total": int(queue_summary["total_messages"]),
                },
                "forecast": {},
                "anomalies": [],
                "queue_backlog": queue_summary["queues"],
                "risk": {
                    "score": 0,
                    "level": "low",
                    "should_alert": False,
                    "reasons": ["empty_metric_series_after_bucketization"],
                },
            }

        current_latency = float(series["latency_p95_ms"][-1])
        current_error = float(series["error_rate"][-1])
        baseline_latency = self._safe_median(series["latency_p95_ms"][:-1] or series["latency_p95_ms"])
        baseline_error = self._safe_median(series["error_rate"][:-1] or series["error_rate"])

        latency_signal = self._detect_series_anomaly(
            metric_name="latency_p95_ms",
            current=current_latency,
            history=series["latency_p95_ms"][:-1] or series["latency_p95_ms"],
            threshold=float(getattr(settings, "AI_ANOMALY_ZSCORE_THRESHOLD", 2.5) or 2.5),
            reason="p95 de latencia acima do padrao historico da janela",
            recommendation="avaliar gargalos de LLM, banco vetorial e broker",
        )
        error_signal = self._detect_series_anomaly(
            metric_name="error_rate",
            current=current_error,
            history=series["error_rate"][:-1] or series["error_rate"],
            threshold=float(getattr(settings, "AI_ANOMALY_ZSCORE_THRESHOLD", 2.5) or 2.5),
            reason="taxa de erro acima do padrao historico da janela",
            recommendation="inspecionar ultimos erros por endpoint e causa raiz",
        )

        anomalies: list[dict[str, Any]] = []
        if latency_signal:
            anomalies.append(latency_signal)
        if error_signal:
            anomalies.append(error_signal)

        backlog_threshold = int(getattr(settings, "AI_ANOMALY_BACKLOG_THRESHOLD", 200) or 200)
        if int(queue_summary["total_messages"]) >= backlog_threshold:
            anomalies.append(
                {
                    "metric": "queue_backlog_total",
                    "severity": "high" if queue_summary["total_messages"] >= backlog_threshold * 2 else "medium",
                    "current": int(queue_summary["total_messages"]),
                    "baseline": int(backlog_threshold),
                    "reason": "backlog agregado de filas acima do limite",
                    "recommendation": "aumentar consumidores e verificar filas sem consumers",
                }
            )

        forecast = {
            "latency_p95_ms_next_30m": self._forecast_next(series["latency_p95_ms"], step_count=3),
            "error_rate_next_30m": self._forecast_next(series["error_rate"], step_count=3),
            "queue_backlog_total_next_30m": self._forecast_backlog(queue_summary["total_messages"]),
        }

        risk = self._risk_from_signals(
            anomalies=anomalies,
            current_error_rate=current_error,
            queue_backlog_total=int(queue_summary["total_messages"]),
        )

        return {
            "status": "ok",
            "window": {
                "start_ts": start_ts,
                "end_ts": end_ts,
                "bucket_minutes": int(bucket_minutes),
                "total_events": len(window_events),
                "bucket_count": len(buckets),
            },
            "current": {
                "latency_p95_ms": round(current_latency, 2),
                "error_rate": round(current_error, 4),
                "queue_backlog_total": int(queue_summary["total_messages"]),
            },
            "baseline": {
                "latency_p95_ms_median": round(baseline_latency, 2),
                "error_rate_median": round(baseline_error, 4),
            },
            "forecast": forecast,
            "anomalies": anomalies,
            "queue_backlog": queue_summary["queues"],
            "risk": risk,
        }

    def _normalize_events(
        self, *, events: list[dict[str, Any]], start_ts: float, end_ts: float
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for ev in events or []:
            try:
                ts = float(ev.get("created_at") or 0.0)
            except Exception:
                ts = 0.0
            if ts <= 0 or ts < start_ts or ts > end_ts:
                continue

            latency = self._safe_float(ev.get("latency_ms"), default=0.0)
            status = str(ev.get("status") or "").strip().lower()
            is_error = status in {"error", "failed", "timeout", "ko"} or status.startswith("5")
            out.append(
                {
                    "created_at": ts,
                    "latency_ms": max(0.0, latency),
                    "is_error": bool(is_error),
                }
            )
        out.sort(key=lambda item: float(item["created_at"]))
        return out

    def _build_buckets(
        self,
        *,
        events: list[dict[str, Any]],
        start_ts: float,
        end_ts: float,
        bucket_seconds: int,
    ) -> list[dict[str, Any]]:
        bucket_count = max(1, int((end_ts - start_ts) / bucket_seconds) + 1)
        buckets: list[dict[str, Any]] = []
        for idx in range(bucket_count):
            b_start = start_ts + (idx * bucket_seconds)
            b_end = b_start + bucket_seconds
            buckets.append(
                {
                    "bucket_start": b_start,
                    "bucket_end": b_end,
                    "latencies": [],
                    "total": 0,
                    "errors": 0,
                }
            )

        for ev in events:
            rel = int((float(ev["created_at"]) - start_ts) / bucket_seconds)
            rel = max(0, min(rel, bucket_count - 1))
            bucket = buckets[rel]
            bucket["total"] += 1
            if ev["is_error"]:
                bucket["errors"] += 1
            if ev["latency_ms"] > 0:
                bucket["latencies"].append(float(ev["latency_ms"]))
        return buckets

    def _extract_series(self, buckets: list[dict[str, Any]]) -> dict[str, list[float]]:
        latency_series: list[float] = []
        error_series: list[float] = []

        for bucket in buckets:
            total = int(bucket["total"])
            lats = list(bucket["latencies"] or [])
            if total <= 0:
                continue
            latency_series.append(self._percentile(lats, 95.0) if lats else 0.0)
            error_series.append(float(bucket["errors"]) / max(1, total))
        return {"latency_p95_ms": latency_series, "error_rate": error_series}

    def _detect_series_anomaly(
        self,
        *,
        metric_name: str,
        current: float,
        history: list[float],
        threshold: float,
        reason: str,
        recommendation: str,
    ) -> dict[str, Any] | None:
        if not history:
            return None
        baseline = self._safe_median(history)
        zscore = self._robust_zscore(current=current, values=history)
        ratio = current / max(0.000001, baseline) if baseline > 0 else (2.0 if current > 0 else 1.0)
        triggered = (zscore >= threshold and current > baseline) or (ratio >= 2.0 and current > baseline)
        if not triggered:
            return None

        severity = "high" if (zscore >= threshold * 1.5 or ratio >= 3.0) else "medium"
        return {
            "metric": metric_name,
            "severity": severity,
            "current": round(current, 4),
            "baseline": round(baseline, 4),
            "deviation_zscore": round(zscore, 4),
            "reason": reason,
            "recommendation": recommendation,
        }

    def _summarize_queues(self, queue_snapshots: list[dict[str, Any]]) -> dict[str, Any]:
        queues: list[dict[str, Any]] = []
        total_messages = 0
        for item in queue_snapshots or []:
            name = str(item.get("name") or item.get("queue") or "unknown")
            messages = int(self._safe_float(item.get("messages"), default=0.0))
            consumers = int(self._safe_float(item.get("consumers"), default=0.0))
            queues.append({"name": name, "messages": messages, "consumers": consumers})
            total_messages += max(0, messages)
        queues.sort(key=lambda q: int(q["messages"]), reverse=True)
        return {"queues": queues, "total_messages": int(total_messages)}

    def _risk_from_signals(
        self,
        *,
        anomalies: list[dict[str, Any]],
        current_error_rate: float,
        queue_backlog_total: int,
    ) -> dict[str, Any]:
        score = 0
        reasons: list[str] = []
        for anomaly in anomalies:
            sev = str(anomaly.get("severity") or "low").lower()
            metric = str(anomaly.get("metric") or "unknown")
            if sev == "high":
                score += 45
            elif sev == "medium":
                score += 30
            else:
                score += 15
            reasons.append(f"{metric}:{sev}")

        if current_error_rate >= 0.20:
            score += 20
            reasons.append("error_rate>=20%")
        if queue_backlog_total >= int(getattr(settings, "AI_ANOMALY_BACKLOG_THRESHOLD", 200) or 200):
            score += 20
            reasons.append("queue_backlog_threshold_exceeded")

        score = max(0, min(100, int(score)))
        level = self._risk_level(score)
        return {
            "score": score,
            "level": level,
            "should_alert": level in {"medium", "high"},
            "reasons": reasons,
        }

    def _backlog_risk(self, total_backlog: int) -> int:
        threshold = int(getattr(settings, "AI_ANOMALY_BACKLOG_THRESHOLD", 200) or 200)
        if total_backlog <= 0:
            return 0
        if total_backlog < threshold:
            return 20
        if total_backlog < threshold * 2:
            return 45
        return 70

    def _risk_level(self, score: int | float) -> str:
        val = float(score)
        if val >= 70:
            return "high"
        if val >= 35:
            return "medium"
        return "low"

    def _forecast_next(self, values: list[float], step_count: int) -> float | None:
        if not values:
            return None
        if len(values) == 1:
            return round(float(values[-1]), 4)
        base = values[-min(4, len(values)) :]
        first = float(base[0])
        last = float(base[-1])
        slope = (last - first) / max(1, len(base) - 1)
        forecast = max(0.0, last + (slope * max(1, int(step_count))))
        return round(forecast, 4)

    def _forecast_backlog(self, backlog_total: int) -> int:
        # Forecast conservador: sem taxa de drenagem medida, assume persistencia do backlog atual.
        return int(max(0, backlog_total))

    def _robust_zscore(self, *, current: float, values: list[float]) -> float:
        if not values:
            return 0.0
        median = self._safe_median(values)
        deviations = [abs(v - median) for v in values]
        mad = self._safe_median(deviations)
        if mad <= 0:
            if current <= median:
                return 0.0
            return 4.0
        return max(0.0, (0.6745 * (current - median)) / mad)

    @staticmethod
    def _safe_median(values: list[float]) -> float:
        cleaned = [float(v) for v in values if v is not None]
        if not cleaned:
            return 0.0
        return float(statistics.median(cleaned))

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(float(v) for v in values)
        if len(sorted_vals) == 1:
            return sorted_vals[0]
        p = max(0.0, min(100.0, float(percentile)))
        rank = (p / 100.0) * (len(sorted_vals) - 1)
        lo = int(rank)
        hi = min(lo + 1, len(sorted_vals) - 1)
        if lo == hi:
            return sorted_vals[lo]
        weight = rank - lo
        return sorted_vals[lo] * (1.0 - weight) + sorted_vals[hi] * weight


_predictive_anomaly_detection_service: PredictiveAnomalyDetectionService | None = None


def get_predictive_anomaly_detection_service() -> PredictiveAnomalyDetectionService:
    global _predictive_anomaly_detection_service
    if _predictive_anomaly_detection_service is None:
        _predictive_anomaly_detection_service = PredictiveAnomalyDetectionService()
    return _predictive_anomaly_detection_service

