"""Gunicorn configuration for Azure App Service.

Key feature: the ``post_fork`` hook calls ``_init_otel()`` in each worker
process **after** ``os.fork()``.  This ensures the ``BatchSpanProcessor``
worker thread is alive in the child process — without this, the thread
created in the master is silently lost after fork and telemetry is never
exported.
"""

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = 1                 # App Service default; scale via instance count
worker_class = "gthread"    # Thread-based to handle concurrent requests
threads = 4
timeout = 600               # Long-running LLM calls

# ---------------------------------------------------------------------------
# Post-fork OTel initialisation
# ---------------------------------------------------------------------------
def post_fork(server, worker):
    """Initialise OpenTelemetry in the worker after os.fork().

    The master process imports the ``app`` module (triggering class
    definitions and Flask app creation) but does NOT call
    ``_init_otel()``.  Each forked worker calls it here so that
    ``configure_azure_monitor()`` starts its ``BatchSpanProcessor``
    background thread in the correct process.
    """
    import app as app_module
    app_module._init_otel()
    app_module._instrument_flask()
    server.log.info("Worker %s: OTel initialised (PID %s)", worker.pid, worker.pid)
