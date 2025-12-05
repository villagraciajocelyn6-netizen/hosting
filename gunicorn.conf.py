# Gunicorn configuration file
import sys

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Performance
workers = 2
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Ensure stdout/stderr are not buffered
def on_starting(server):
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print("=" * 80, flush=True)
    print("Gunicorn starting with console logging enabled", flush=True)
    print("=" * 80, flush=True)
