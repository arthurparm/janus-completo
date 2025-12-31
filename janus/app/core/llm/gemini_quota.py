
import logging
import os
import time
from typing import Optional, Dict, Any
from google.cloud import monitoring_v3
from app.config import settings
from .rate_limiter import get_rate_limiter, RateLimitConfig

logger = logging.getLogger(__name__)

class GeminiQuotaFetcher:
    """
    Fetches Gemini quotas from Google Cloud Monitoring API.
    Requires 'Monitoring Viewer' role for the service account.
    """
    
    def __init__(self, project_id: str = "orbisfracta", key_path: Optional[str] = None):
        self.project_id = project_id
        # Use env var directly or fallback to known docker path
        self.key_path = key_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "/app/app/serviceAccountKey.json"
        
        # Ensure env var is set for the library
        if self.key_path and os.path.exists(self.key_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.key_path
        
        self._client: Optional[monitoring_v3.MetricServiceClient] = None

    def _get_client(self) -> Optional[monitoring_v3.MetricServiceClient]:
        if self._client:
            return self._client
            
        if not os.path.exists(self.key_path):
            logger.warning(f"Service Account Key not found at {self.key_path}. Cannot fetch Gemini quotas.")
            return None
            
        try:
            self._client = monitoring_v3.MetricServiceClient()
            return self._client
        except Exception as e:
            logger.error(f"Failed to initialize MetricServiceClient: {e}")
            return None

    def fetch_and_update_limits(self):
        """Fetches quotas and updates the global RateLimiter."""
        client = self._get_client()
        if not client:
            return

        project_name = f"projects/{self.project_id}"
        metric_type = "serviceruntime.googleapis.com/quota/limit"
        
        # Filter for Generative Language API
        filter_str = f'metric.type = "{metric_type}" AND resource.labels.service = "generativelanguage.googleapis.com"'
        
        now = time.time()
        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(now)},
                "start_time": {"seconds": int(now) - 3600}, # Look back 1 hour
            }
        )
        
        try:
            logger.info(f"Fetching Gemini quotas from Cloud Monitoring for {self.project_id}...")
            results = client.list_time_series(
                request={
                    "name": project_name,
                    "filter": filter_str,
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                }
            )
            
            count = 0
            for result in results:
                self._process_quota_metric(result)
                count += 1
            
            if count == 0:
                logger.warning("No Gemini quota metrics found. Check if Generative Language API is enabled and used.")
            else:
                logger.info(f"Updated Gemini limits from {count} metrics.")
                
        except Exception as e:
            if "Permission denied" in str(e):
                logger.error("Permission denied fetching Gemini quotas. Ensure Service Account has 'Monitoring Viewer' role.")
            else:
                logger.error(f"Error fetching Gemini quotas: {e}")

    def _process_quota_metric(self, result: Any):
        """Process a single time series result and update RateLimiter."""
        # Labels usually contain method or model info
        # Example labels: {'method': 'GenerateContent', 'quota_metric': '...requests_per_minute...'}
        metric_labels = dict(result.metric.labels)
        resource_labels = dict(result.resource.labels)
        
        # Extract limit value
        limit_value = 0
        for point in result.points:
            limit_value = point.value.int64_value
            break
            
        if limit_value <= 0:
            return

        # Identify what this limit is for
        # Common quota metrics:
        # - .../generate_content_requests_per_minute_per_project_per_base_model
        # - .../input_token_limit
        
        # We try to map it to our RateLimitConfig
        # Since we don't get exact model names easily from generic quotas unless specified in labels,
        # we might apply this to all Gemini models or specific ones if labels exist.
        
        # Heuristic mapping
        quota_name = metric_labels.get("quota_metric", "")
        method = metric_labels.get("method", "")
        
        # Default config updates
        config_update = {}
        
        if "requests_per_minute" in quota_name or "requests_per_minute" in metric_labels.values():
            config_update["rpm"] = limit_value
        elif "requests_per_day" in quota_name:
            config_update["rpd"] = limit_value
        elif "tokens_per_minute" in quota_name:
            config_update["tpm"] = limit_value
        elif "tokens_per_day" in quota_name:
            config_update["tpd"] = limit_value
            
        if not config_update:
            return

        # Apply to known Gemini models
        # If the metric has a 'model' label, use it. Otherwise apply to common ones.
        target_model = metric_labels.get("model", "")
        
        models_to_update = []
        if target_model:
            models_to_update.append(target_model)
        else:
            # Apply to common Gemini models if it's a general quota
            models_to_update = ["gemini-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
            
        rate_limiter = get_rate_limiter()
        provider = "google_gemini"
        
        for model in models_to_update:
            # We need to merge with existing config if possible, but RateLimiter.configure_limits overwrites.
            # Ideally we read existing, update, and write back. 
            # But RateLimiter doesn't expose "get_config".
            # For now, we just create a config. 
            # TODO: Improve RateLimiter to allow partial updates or get_config.
            
            # Since we can't easily read back, we construct a new config. 
            # This might overwrite manually set limits, but API limits should be truth.
            
            # However, since we might get RPM and TPM in different iterations, we should be careful.
            # Let's assume RateLimiter needs a partial update method.
            pass
            
            # For now, let's just log what we found
            logger.info(f"Discovered quota for {model}: {config_update}")
            
            # We will use a private method or modify RateLimiter to support partial updates
            # Or just store it in a local dict and apply at end?
            
            # Let's modify RateLimiter to support partial update or 'update_limits'
            rate_limiter.update_model_limits(provider, model, **config_update)

