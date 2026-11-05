"""DEV-02 opt-in WSGI settings; loading this file does not start a server.

The application factory argument must be supplied explicitly on the command line.
Loopback binding is for a future proxy on the same host, not a Docker topology.
"""

bind = "127.0.0.1:8000"
workers = 2
worker_class = "sync"
threads = 1
timeout = 30
graceful_timeout = 30
preload_app = False
reload = False
daemon = False

# TrustedProxy alone validates the socket peer and reconstructs HTTPS metadata.
# Do not let the WSGI server independently trust or rewrite forwarded headers.
secure_scheme_headers = {}
forwarded_allow_ips = ""
forwarder_headers = ""  # Gunicorn validates a CSV string; resolves to an empty list.
proxy_protocol = False

# No URL/query access log, no config dump or DEBUG output containing app settings.
accesslog = None
errorlog = "-"
loglevel = "warning"
capture_output = False
