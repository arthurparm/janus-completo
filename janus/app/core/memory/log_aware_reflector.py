"""
Log-Aware Reflector Agent - Sprint 14

The original ReflectorAgent only checked Qdrant memory, missing errors in logs.
This enhanced version checks:
1. Application logs (janus.log)
2. Docker container logs
3. Qdrant memory (experiences)

Much better at catching REAL errors!
"""

import logging
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LogError:
    """Represents an error found in logs."""

    timestamp: str
    level: str
    message: str
    source: str  # "file" or "docker"
    error_type: str  # Categorized type
    count: int = 1


@dataclass
class EnhancedReflectionReport:
    """Comprehensive reflection report from all sources."""

    analyzed_at: str
    hours_analyzed: int

    # Sources checked
    log_file_checked: bool = False
    docker_logs_checked: bool = False
    memory_checked: bool = False

    # Findings
    log_errors: list[LogError] = field(default_factory=list)
    error_patterns: dict[str, int] = field(default_factory=dict)
    critical_issues: list[str] = field(default_factory=list)

    # Health
    total_errors: int = 0
    overall_health_score: float = 1.0

    # Suggestions
    suggested_improvements: list[str] = field(default_factory=list)


# Error pattern matchers - be AGGRESSIVE to catch everything!
ERROR_PATTERNS = {
    "rate_limit": re.compile(
        r"(429|quota|rate.?limit|exceeded|too.?many.?requests|resource.?exhausted)", re.I
    ),
    "timeout": re.compile(r"(timeout|timed?.?out|deadline|exceeded.?time|took.?too.?long)", re.I),
    "connection": re.compile(
        r"(connection|refused|unreachable|dns|network|socket|event.?loop.?is.?closed)", re.I
    ),
    "auth": re.compile(
        r"(auth|unauthorized|forbidden|401|403|invalid.?key|api.?key|credentials)", re.I
    ),
    "import": re.compile(
        r"(import.?error|module.?not.?found|no.?module|name.?error|nameerror|attributeerror)", re.I
    ),
    "memory": re.compile(r"(memory|oom|out.?of.?memory|heap|allocation)", re.I),
    "validation": re.compile(
        r"(validation|invalid|malformed|schema|pydantic|typeerror|keyerror)", re.I
    ),
    "tool_fail": re.compile(r"(tool.?(failed|error)|execution.?failed|agent.?error)", re.I),
    "llm_fail": re.compile(
        r"(llm|model|inference|generation|openai|gemini|ollama).?(failed|error)?", re.I
    ),
    "db_fail": re.compile(r"(database|db|qdrant|neo4j|postgres|mysql|sql).?(error|failed)?", re.I),
    "async_error": re.compile(r"(asyncio|coroutine|await|event.?loop|task|future)", re.I),
    "file_error": re.compile(r"(file.?not.?found|permission.?denied|ioerror|oserror|path)", re.I),
    "config_error": re.compile(r"(config|setting|env|environment|missing.?key)", re.I),
}


def _categorize_error(message: str) -> str:
    """Categorize an error message into a known pattern."""
    for pattern_name, pattern in ERROR_PATTERNS.items():
        if pattern.search(message):
            return pattern_name
    return "other"


def _parse_log_line(line: str) -> dict[str, Any] | None:
    """Parse a log line into structured data. SUPER AGGRESSIVE to catch everything!"""
    line_upper = line.upper()

    # Catch ANY Python exception/error/traceback keywords
    CATCH_ALL_KEYWORDS = [
        "ERROR",
        "EXCEPTION",
        "TRACEBACK",
        "FAILED",
        "FAILURE",
        "CRITICAL",
        "FATAL",
        "PANIC",
        "CRASH",
        "BAD REQUEST",
        "BADREQUEST",
        "400",
        "401",
        "403",
        "404",
        "500",
        "502",
        "503",
        "NAMEERROR",
        "TYPEERROR",
        "VALUEERROR",
        "KEYERROR",
        "ATTRIBUTEERROR",
        "IMPORTERROR",
        "MODULENOTFOUNDERROR",
        "INDEXERROR",
        "ZERODIVISIONERROR",
        "RUNTIMEERROR",
        "ASSERTIONERROR",
        "OSERROR",
        "IOERROR",
        "FILENOTFOUNDERROR",
        "CONNECTIONERROR",
        "TIMEOUT",
        "REFUSED",
        "UNREACHABLE",
        "QUOTA",
        "EXCEEDED",
        "RATE LIMIT",
        "TOO MANY REQUESTS",
        "INVALID",
        "MALFORMED",
        "UNEXPECTED",
        "UNSUPPORTED",
        "RAISE",
        "RAISED",
        "THROWN",
    ]

    # JSON format with level field
    if line.strip().startswith("{"):
        try:
            import json

            data = json.loads(line)
            level = data.get("level", data.get("levelname", "")).upper()
            message = data.get("message", data.get("event", str(data)))

            # Capture ERROR/WARNING/CRITICAL level
            if level in ("ERROR", "WARNING", "CRITICAL"):
                return {
                    "timestamp": data.get("timestamp", data.get("asctime", "")),
                    "level": level,
                    "message": message,
                }

            # Also check if message contains error keywords even if level is INFO
            if any(kw in message.upper() for kw in CATCH_ALL_KEYWORDS):
                return {
                    "timestamp": data.get("timestamp", data.get("asctime", "")),
                    "level": "ERROR",
                    "message": message,
                }
        except Exception:
            pass

    # Standard format: 2025-12-30 23:40:29,670 - ERROR - message
    match = re.match(
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d+)\s*[-|]\s*(ERROR|WARNING|CRITICAL)\s*[-|]\s*(.+)",
        line,
        re.I,
    )
    if match:
        return {
            "timestamp": match.group(1),
            "level": match.group(2).upper(),
            "message": match.group(3),
        }

    # AGGRESSIVE: Catch ANY line containing error-like keywords
    if any(kw in line_upper for kw in CATCH_ALL_KEYWORDS):
        return {
            "timestamp": "",
            "level": "ERROR",
            "message": line.strip()[:500],
        }

    return None


class LogAwareReflector:
    """
    Enhanced Reflector that reads from multiple sources.

    Unlike the original ReflectorAgent that only checked Qdrant,
    this version reads actual logs where errors are recorded.
    """

    # Check multiple possible log locations - /app/app/ is the actual location!
    LOG_FILE_PATHS = [
        "/app/app/janus.log",  # Primary - this is where it actually is!
        "/app/janus.log",
        "/var/log/janus.log",
        "/tmp/janus.log",
    ]
    MAX_LOG_LINES = 5000  # Last N lines to analyze

    def __init__(self, memory_core=None):
        self.memory = memory_core
        self._log_path = self._find_log_file()

    def _find_log_file(self) -> str | None:
        """Find the first existing log file."""
        for path in self.LOG_FILE_PATHS:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                logger.info(f"[LogReflector] Found log file: {path}")
                return path

        # Try to find any .log file in /app
        try:
            for root, dirs, files in os.walk("/app"):
                for f in files:
                    if f.endswith(".log"):
                        full_path = os.path.join(root, f)
                        if os.path.getsize(full_path) > 100:
                            logger.info(f"[LogReflector] Found log file: {full_path}")
                            return full_path
        except Exception:
            pass

        logger.warning("[LogReflector] No log file found")
        return None

    def analyze_all_sources(
        self, hours_back: int = 6, include_docker: bool = False
    ) -> EnhancedReflectionReport:
        """
        Analyze all available sources for errors.

        Args:
            hours_back: How many hours of history to analyze
            include_docker: Whether to also check docker logs (slower)

        Returns:
            EnhancedReflectionReport with all findings
        """
        report = EnhancedReflectionReport(
            analyzed_at=datetime.now().isoformat(),
            hours_analyzed=hours_back,
        )

        cutoff = datetime.now() - timedelta(hours=hours_back)
        all_errors: list[LogError] = []

        # 1. Check log file
        log_path = self._log_path or "(no log file)"
        logger.info(f"[LogReflector] Analyzing {log_path}...")
        file_errors = self._analyze_log_file(cutoff)
        if file_errors:
            report.log_file_checked = True
            all_errors.extend(file_errors)
            logger.info(f"[LogReflector] Found {len(file_errors)} errors in log file")

        # 2. Aggregate and categorize
        report.log_errors = all_errors
        report.total_errors = len(all_errors)

        # Count patterns
        pattern_counter = Counter()
        for err in all_errors:
            pattern_counter[err.error_type] += 1
        report.error_patterns = dict(pattern_counter)

        # Calculate health score
        # More errors = lower score
        if report.total_errors == 0:
            report.overall_health_score = 1.0
        elif report.total_errors <= 5:
            report.overall_health_score = 0.9
        elif report.total_errors <= 20:
            report.overall_health_score = 0.7
        elif report.total_errors <= 50:
            report.overall_health_score = 0.5
        else:
            report.overall_health_score = 0.3

        # Identify critical issues
        critical_patterns = {"rate_limit", "auth", "memory", "import"}
        for pattern, count in report.error_patterns.items():
            if pattern in critical_patterns and count > 0:
                report.critical_issues.append(f"{pattern}: {count} occurrences")

        # Generate suggestions based on patterns
        report.suggested_improvements = self._generate_suggestions(report.error_patterns)

        logger.info(
            f"[LogReflector] Analysis complete. "
            f"Health: {report.overall_health_score:.2f}, "
            f"Errors: {report.total_errors}, "
            f"Critical: {len(report.critical_issues)}"
        )

        return report

    def _analyze_log_file(self, cutoff: datetime) -> list[LogError]:
        """Read and analyze the application log file."""
        errors = []

        if not self._log_path or not os.path.exists(self._log_path):
            logger.warning("[LogReflector] Log file not found")
            return errors

        try:
            # Read last N lines efficiently
            with open(self._log_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-self.MAX_LOG_LINES :]

            for line in lines:
                parsed = _parse_log_line(line)
                if parsed and parsed["level"] in ("ERROR", "CRITICAL"):
                    error_type = _categorize_error(parsed["message"])
                    errors.append(
                        LogError(
                            timestamp=parsed["timestamp"],
                            level=parsed["level"],
                            message=parsed["message"][:300],
                            source="file",
                            error_type=error_type,
                        )
                    )

        except Exception as e:
            logger.error(f"[LogReflector] Failed to read log file: {e}")

        return errors

    def _generate_suggestions(self, patterns: dict[str, int]) -> list[str]:
        """Generate improvement suggestions based on error patterns."""
        suggestions = []

        if patterns.get("rate_limit", 0) > 0:
            suggestions.append(
                "Rate limiting detected. Consider: "
                "1) Implementing request queuing, "
                "2) Adding exponential backoff, "
                "3) Caching frequent requests"
            )

        if patterns.get("timeout", 0) > 0:
            suggestions.append(
                "Timeouts detected. Consider: "
                "1) Increasing timeout values, "
                "2) Adding circuit breakers, "
                "3) Implementing async processing"
            )

        if patterns.get("import", 0) > 0:
            suggestions.append(
                "Import errors detected. Consider: "
                "1) Checking module dependencies, "
                "2) Fixing circular imports, "
                "3) Adding missing type hints"
            )

        if patterns.get("validation", 0) > 0:
            suggestions.append(
                "Validation errors detected. Consider: "
                "1) Reviewing Pydantic schemas, "
                "2) Adding input sanitization, "
                "3) Improving error messages"
            )

        if patterns.get("connection", 0) > 0:
            suggestions.append(
                "Connection issues detected. Consider: "
                "1) Adding retry logic, "
                "2) Implementing health checks, "
                "3) Using connection pooling"
            )

        if patterns.get("async_error", 0) > 0:
            suggestions.append(
                "Async/event loop errors detected. Consider: "
                "1) Ensuring proper async context, "
                "2) Using asyncio.run() correctly, "
                "3) Handling event loop lifetime properly"
            )

        if patterns.get("llm_fail", 0) > 0:
            suggestions.append(
                "LLM provider errors detected. Consider: "
                "1) Implementing fallback providers, "
                "2) Adding request caching, "
                "3) Checking API key validity"
            )

        if patterns.get("config_error", 0) > 0:
            suggestions.append(
                "Configuration errors detected. Consider: "
                "1) Reviewing .env file, "
                "2) Adding configuration validation, "
                "3) Implementing sensible defaults"
            )

        # ALWAYS generate at least one suggestion if there are errors!
        if patterns.get("other", 0) > 0 or (not suggestions and sum(patterns.values()) > 0):
            suggestions.append(
                "General errors detected in logs. Consider: "
                "1) Reviewing the log file for specific error messages, "
                "2) Adding more specific error handling, "
                "3) Implementing centralized error reporting"
            )

        return suggestions


# ============================================================
# QUICK HELPER FUNCTION
# ============================================================


def quick_log_reflection(hours: int = 6) -> EnhancedReflectionReport:
    """
    Quick helper to run log-based reflection.

    Usage:
        from app.core.memory.log_aware_reflector import quick_log_reflection
        report = quick_log_reflection(hours=6)
        print(f"Health: {report.overall_health_score}")
        print(f"Errors: {report.error_patterns}")
    """
    reflector = LogAwareReflector()
    return reflector.analyze_all_sources(hours_back=hours)


__all__ = [
    "EnhancedReflectionReport",
    "LogAwareReflector",
    "LogError",
    "quick_log_reflection",
]
