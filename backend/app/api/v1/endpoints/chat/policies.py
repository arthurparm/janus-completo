import os


def confidence_confirmation_threshold() -> float:
    raw = os.getenv("CHAT_CONFIDENCE_CONFIRMATION_THRESHOLD", "0.65").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.65


def confidence_band(confidence: float) -> str:
    if confidence >= 0.80:
        return "high"
    if confidence >= 0.60:
        return "medium"
    return "low"
