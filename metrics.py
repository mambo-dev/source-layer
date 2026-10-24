
import time


def update_metric_file(metric_name, metric_perf, metric_file_path="metrics/metrics.txt"):
    metric_detail = (F"METRIC_NAME: {metric_name}\n"
                     f"METRIC PERFOMANCE: {metric_perf} seconds \n"
                     f"TIMESTAMP: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                     "----------------------------------------\n")
    
    with open(metric_file_path, "a", encoding="utf-8") as file:
        file.write(metric_detail)