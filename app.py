# app.py
from fastapi import FastAPI, Request, Response, HTTPException
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
import time
import random
import os

app = FastAPI(title="monitoring-demo-app")

# Use default registry so Prometheus client libs work out-of-the-box.
REQUEST_COUNT = Counter(
    "app_requests_total",
    "Total HTTP requests processed",
    ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "app_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"]
)

IN_PROGRESS = Gauge(
    "app_inprogress_requests",
    "Number of in-progress requests"
)

ERROR_COUNT = Counter(
    "app_exceptions_total",
    "Total exceptions raised by the application",
    ["exception_type"]
)

# Example business metric (could be orders processed, tasks completed, etc.)
BUSINESS_PROCESSED = Counter(
    "app_business_items_processed_total",
    "Number of business items processed"
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to measure request count, latency, in-progress gauge, and status code."""
    method = request.method
    path = request.url.path
    IN_PROGRESS.inc()
    start = time.time()
    try:
        response: Response = await call_next(request)
        status = str(response.status_code)
        return response
    except Exception as exc:
        ERROR_COUNT.inc(type(exc).__name__)
        # re-raise so FastAPI's handlers/logging still run
        raise
    finally:
        elapsed = time.time() - start
        REQUEST_LATENCY.labels(method=method, endpoint=path).observe(elapsed)
        # Use 500 if exception prevented generating response
        try:
            status_label = status
        except UnboundLocalError:
            status_label = "500"
        REQUEST_COUNT.labels(method=method, endpoint=path, http_status=status_label).inc()
        IN_PROGRESS.dec()

@app.get("/")
async def root():
    """Simple root endpoint."""
    return {"status": "ok", "message": "Monitoring demo app"}

@app.get("/process")
async def process(count: int = 1):
    """
    Example endpoint that simulates some processing.
    Query param 'count' increases the business metric accordingly.
    """
    # simulate variable work
    sleep_for = random.uniform(0.05, 0.5)
    time.sleep(sleep_for)

    # increase business metric
    BUSINESS_PROCESSED.inc(count)

    # intentionally sometimes raise a 500 to generate error metrics (simulate)
    if random.random() < 0.05:
        raise HTTPException(status_code=500, detail="Simulated transient error")

    return {"processed": count, "took_seconds": round(sleep_for, 3)}

@app.get("/health")
async def health():
    """Readiness / liveness endpoint."""
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Exposes the default registry metrics collected above.
    """
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
