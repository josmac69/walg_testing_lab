#!/usr/bin/env python3
import http.server
import json
import os
import subprocess
import time
from datetime import datetime

PORT = 9351
CACHE_DURATION = 10  # seconds
last_cache_time = 0
cached_metrics = ""

def get_walg_metrics():
    global last_cache_time, cached_metrics
    now = time.time()
    if now - last_cache_time < CACHE_DURATION and cached_metrics:
        return cached_metrics

    # Default metrics
    backup_count = 0
    last_backup_timestamp = 0
    last_backup_uncompressed_bytes = 0
    last_backup_compressed_bytes = 0
    last_backup_duration_seconds = 0
    scrape_success = 1

    try:
        # Run WAL-G backup-list
        cmd = ["/usr/local/bin/wal-g", "backup-list", "--json", "--detail"]
        env = os.environ.copy()
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, check=True)
        
        # Parse JSON
        output = result.stdout
        if "[" in output:
            output = output[output.index("["):]
        
        backups = json.loads(output)
        backup_count = len(backups)
        
        if backup_count > 0:
            # Sort backups by finished time
            def parse_time(t_str):
                for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
                    try:
                        return datetime.strptime(t_str, fmt)
                    except ValueError:
                        pass
                return datetime.min

            backups.sort(key=lambda x: parse_time(x.get("time", "")))
            latest = backups[-1]
            
            # Extract timestamp
            t_str = latest.get("time", "")
            t_obj = parse_time(t_str)
            if t_obj != datetime.min:
                last_backup_timestamp = t_obj.timestamp()
            
            # Extract sizes
            last_backup_uncompressed_bytes = latest.get("uncompressed_size", 0)
            last_backup_compressed_bytes = latest.get("compressed_size", 0)
            
            # Extract duration
            start_str = latest.get("start_time", "")
            finish_str = latest.get("finish_time", "")
            start_obj = parse_time(start_str)
            finish_obj = parse_time(finish_str)
            if start_obj != datetime.min and finish_obj != datetime.min:
                last_backup_duration_seconds = (finish_obj - start_obj).total_seconds()

    except Exception as e:
        print(f"Error gathering metrics: {e}")
        scrape_success = 0

    # Format Prometheus metrics
    lines = [
        "# HELP walg_scrape_success 1 if the exporter successfully queried WAL-G, 0 otherwise.",
        "# TYPE walg_scrape_success gauge",
        f"walg_scrape_success {scrape_success}",
        "# HELP walg_backups_total Total number of WAL-G base backups found in storage.",
        "# TYPE walg_backups_total gauge",
        f"walg_backups_total {backup_count}",
        "# HELP walg_last_backup_timestamp Epoch timestamp of the last completed WAL-G base backup.",
        "# TYPE walg_last_backup_timestamp gauge",
        f"walg_last_backup_timestamp {last_backup_timestamp}",
        "# HELP walg_last_backup_uncompressed_bytes Uncompressed size in bytes of the last WAL-G base backup.",
        "# TYPE walg_last_backup_uncompressed_bytes gauge",
        f"walg_last_backup_uncompressed_bytes {last_backup_uncompressed_bytes}",
        "# HELP walg_last_backup_compressed_bytes Compressed size in bytes of the last WAL-G base backup.",
        "# TYPE walg_last_backup_compressed_bytes gauge",
        f"walg_last_backup_compressed_bytes {last_backup_compressed_bytes}",
        "# HELP walg_last_backup_duration_seconds Duration in seconds of the last WAL-G base backup.",
        "# TYPE walg_last_backup_duration_seconds gauge",
        f"walg_last_backup_duration_seconds {last_backup_duration_seconds}"
    ]
    
    cached_metrics = "\n".join(lines) + "\n"
    last_cache_time = now
    return cached_metrics

class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_walg_metrics().encode("utf-8"))
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>WAL-G Prometheus Exporter</h1><a href='/metrics'>Metrics</a></body></html>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Quiet requests logging to avoid filling Docker Compose logs
        pass

if __name__ == "__main__":
    print(f"Starting WAL-G Prometheus Exporter on port {PORT}...")
    server = http.server.HTTPServer(("", PORT), MetricsHandler)
    server.serve_forever()
