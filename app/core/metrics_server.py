from http.server import BaseHTTPRequestHandler, HTTPServer

from prometheus_client import (
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
    generate_latest,
    multiprocess,
)


class MetricsHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path != "/metrics":
            self.send_error(404)
            return

        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)

        data = generate_latest(registry)

        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9101), MetricsHandler).serve_forever()