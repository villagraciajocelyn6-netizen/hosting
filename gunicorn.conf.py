import os

# Server socket - Render provides PORT as environment variable
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Worker processes
workers = 2
worker_class = 'sync'
timeout = 30
keepalive = 2

# Logging
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = 'info'
capture_output = True
enable_stdio_inheritance = True

# Disable buffering
raw_env = ['PYTHONUNBUFFERED=1']

def on_starting(server):
    import sys
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print("=" * 80, flush=True)
    print("🚀 PYTHON SCRIPT EXECUTOR STARTING ON RENDER", flush=True)
    print(f"Binding to: {bind}", flush=True)
    print(f"Workers: {workers}", flush=True)
    print("=" * 80, flush=True)

def when_ready(server):
    print("\n✅ Server is ready and accepting connections!\n", flush=True)
