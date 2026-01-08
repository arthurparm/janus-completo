
import os
import time
from google.cloud import monitoring_v3

# Point to the service account key
key_path = "/app/app/serviceAccountKey.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
project_id = "orbisfracta"

def list_quota_metrics():
    print(f"Using key: {key_path}")
    if not os.path.exists(key_path):
        print("Key file not found!")
        return

    try:
        client = monitoring_v3.MetricServiceClient()
    except Exception as e:
        print(f"Error initializing client: {e}")
        return

    project_name = f"projects/{project_id}"
    
    print(f"Listing quota metrics for {project_name}...")
    
    # Filter for quota metrics
    filter_str = 'metric.type = starts_with("serviceruntime.googleapis.com/quota") AND resource.labels.service = "generativelanguage.googleapis.com"'
    
    try:
        # Fix: use request dictionary or object
        results = client.list_metric_descriptors(request={"name": project_name, "filter": filter_str})
        found = False
        for descriptor in results:
            found = True
            print(f"\nMetric: {descriptor.type}")
            print(f"Display Name: {descriptor.display_name}")
            print(f"Description: {descriptor.description}")

        if not found:
            print("No metrics found with specific filter. Checking permissions with broad filter...")
            filter_str = 'metric.type = starts_with("serviceruntime.googleapis.com/quota")'
            results = client.list_metric_descriptors(request={"name": project_name, "filter": filter_str})
            count = 0
            for descriptor in results:
                print(f" - {descriptor.type}")
                count += 1
                if count > 5: break
            if count == 0:
                print("No quota metrics found at all.")
            
    except Exception as e:
        print(f"Error listing metrics: {e}")

def get_quota_values():
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"
    
    metric_type = "serviceruntime.googleapis.com/quota/limit"
    filter_str = f'metric.type = "{metric_type}" AND resource.labels.service = "generativelanguage.googleapis.com"'
    
    now = time.time()
    interval = monitoring_v3.TimeInterval(
        {
            "end_time": {"seconds": int(now)},
            "start_time": {"seconds": int(now) - 3600},
        }
    )
    
    print(f"\nFetching time series for {metric_type}...")
    try:
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
            print("\n--- Quota Limit ---")
            print(f"Metric Labels: {result.metric.labels}")
            
            for point in result.points:
                print(f"Value: {point.value.int64_value}")
                break
            count += 1
            if count > 5: break
        
        if count == 0:
            print("No time series data returned.")
                
    except Exception as e:
        print(f"Error fetching time series: {e}")

if __name__ == "__main__":
    list_quota_metrics()
    get_quota_values()
