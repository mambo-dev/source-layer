
import time
from prometheus_client import Counter, Histogram

EMBEDDING_BATCH_DURATION = Histogram(
    "document_embedding_batch_duration_seconds",
    "Duration of embedding generation per batch",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300, 600, float("inf"))
)

EMBEDDED_CHUNKS = Counter(
    "document_embedding_chunks_total",
    "Number of chunks successfully embedded"
)

EMBEDDING_BATCH_FAILURES = Counter(
    "document_embedding_batch_failures_total",
    "Number of failed embedding batch attempts"
)

def update_metric_file(metric_name, metric_perf, metric_file_path="metrics/metrics.txt"):
    metric_detail = (F"METRIC_NAME: {metric_name}\n"
                     f"METRIC PERFOMANCE: {metric_perf} seconds \n"
                     f"TIMESTAMP: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                     "----------------------------------------\n")
    
    with open(metric_file_path, "a", encoding="utf-8") as file:
        file.write(metric_detail)