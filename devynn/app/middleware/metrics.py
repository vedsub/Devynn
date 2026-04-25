import os
import time
import threading
from collections import deque
import boto3
from starlette.middleware.base import BaseHTTPMiddleware


class CloudWatchMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._buffer = deque()
        self._lock = threading.Lock()
        self._cw = boto3.client("cloudwatch", region_name=os.environ.get("AWS_REGION", "us-east-1"))

    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        
        metrics = [
            {
                "MetricName": "RequestLatencyMs",
                "Value": latency_ms,
                "Unit": "Milliseconds",
                "Dimensions": [{"Name": "Route", "Value": request.url.path}]
            },
            {
                "MetricName": "RequestCount",
                "Value": 1,
                "Unit": "Count",
                "Dimensions": [{"Name": "StatusCode", "Value": str(response.status_code)}]
            },
        ]
        
        if request.url.path in ("/upload", "/upload/stream"):
            cache_val = 1 if response.headers.get("X-Cache") == "HIT" else 0
            metrics.append({
                "MetricName": "CacheHit",
                "Value": cache_val,
                "Unit": "Count"
            })
            
        with self._lock:
            self._buffer.extend(metrics)
            if len(self._buffer) >= 20: 
                self._flush()
                
        return response

    def _flush(self):
        batch = [self._buffer.popleft() for _ in range(min(20, len(self._buffer)))]
        try: 
            self._cw.put_metric_data(Namespace="Devynn/API", MetricData=batch)
        except Exception: 
            pass  # never block on metrics failure
