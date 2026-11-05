"""DEV-04 container-only settings; not selected by the legacy/local entrypoints.

Listening on container interfaces does not publish a host port. The dedicated
Compose descriptor publishes no backend port and remains explicitly blocked.
"""

bind = "0.0.0.0:8000"
workers = 2
worker_class = "sync"
threads = 1
timeout = 30
graceful_timeout = 30
worker_tmp_dir = "/tmp"
preload_app = False
reload = False
daemon = False
secure_scheme_headers = {}
forwarded_allow_ips = ""
forwarder_headers = ""  # Gunicorn validates a CSV string; resolves to an empty list.
proxy_protocol = False
accesslog = None
errorlog = "-"
loglevel = "warning"
capture_output = False
