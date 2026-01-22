import json
from typing import Any, List, Optional
import structlog
from fastapi import Request, Depends

from app.services.observability_service import ObservabilityService, get_observability_service

logger = structlog.get_logger(__name__)

class TraceService:
    """
    Service responsible for retrieving and formatting agent execution traces.
    It acts as a layer above ObservabilityService to provide specialized views for the frontend.
    """
    def __init__(self, observability_service: ObservabilityService):
        self._obs = observability_service

    def get_trace_history(self, conversation_id: str) -> List[dict[str, Any]]:
        """
        Retrieves the execution trace (Chain of Thought) for a given conversation.
        """
        endpoint = f"chat_event:{conversation_id}"
        # Fetch events, reasonable limit
        events = self._obs.get_audit_events(
            user_id=None,
            tool=None,
            status=None,
            start_ts=None,
            end_ts=None,
            endpoint=endpoint,
            limit=500
        )
        
        # Sort by timestamp ascending to reconstruct the timeline
        events.sort(key=lambda x: x.get("created_at") or 0)

        trace = []
        for ev in events:
            step = self._format_trace_step(ev)
            if step:
                trace.append(step)
        return trace

    def _format_trace_step(self, event: dict[str, Any]) -> Optional[dict[str, Any]]:
        """
        Formats a raw audit event into a standardized trace step.
        """
        # details_json contains the original payload logged by ChatEventDbLogger
        details_str = event.get("details_json")
        if not details_str:
            return None
        
        try:
            payload = json.loads(details_str)
        except Exception:
            return None

        # Standardize schema for Frontend
        return {
            "stepId": str(event.get("id")),
            "timestamp": event.get("created_at"),
            "agent": event.get("tool"), # agent_role
            "type": event.get("action"), # event_type (e.g. AgentThinking, AgentAction)
            "content": payload.get("content"),
            "metadata": {
                 "task_id": payload.get("task_id"),
                 "trace_id": event.get("trace_id"),
                 "model": payload.get("model")
            }
        }

def get_trace_service(
    observability_service: ObservabilityService = Depends(get_observability_service)
) -> TraceService:
    return TraceService(observability_service)
