"""
Web UI for Azure AI Agent Service Chat Bot
Flask-based web interface with thread-based conversations
"""

import os
import time
import logging
import asyncio
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from agent import ChatBotAgent

# Load environment variables
load_dotenv()

# ---------------------------------------------------------------------------
# Azure AI Foundry Tracing – Environment Variables
# ---------------------------------------------------------------------------
# Per the Microsoft Foundry Classic docs ("Instrument the OpenAI SDK"):
#   https://learn.microsoft.com/azure/ai-foundry/how-to/develop/trace-application
#
# OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT – Tells the
#   opentelemetry-instrumentation-openai-v2 instrumentor to record LLM
#   input/output content as span events.  These events populate the
#   "Input" and "Output" columns in the Foundry Classic Tracing blade.
#   Set to "false" in production if prompt content is sensitive.
# ---------------------------------------------------------------------------
os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")

# Set OTEL_SERVICE_NAME so the Foundry Tracing blade can identify these traces.
os.environ.setdefault("OTEL_SERVICE_NAME", os.getenv("AZURE_AI_PROJECT_NAME", "grc-agent"))

# ---------------------------------------------------------------------------
# Application Insights / Azure Monitor OpenTelemetry
# ---------------------------------------------------------------------------
# Configure the Azure Monitor OpenTelemetry distro **before** creating the
# Flask app so that the Flask instrumentor is activated automatically.
# The SDK reads APPLICATIONINSIGHTS_CONNECTION_STRING from the environment.
# ---------------------------------------------------------------------------
from opentelemetry import trace
from opentelemetry.sdk._logs import LogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor


class _EventNameInjector(LogRecordProcessor):
    """Copies ``LogRecord.event_name`` into ``attributes["event.name"]``.

    The ``opentelemetry-instrumentation-openai-v2`` instrumentor creates
    LogRecords with ``event_name`` set (e.g. ``"gen_ai.user.message"``,
    ``"gen_ai.choice"``) via the OTel Events/Logs API.  However, the
    Azure Monitor exporter (v1.0.0b48) only reads ``log_record.attributes``
    when building ``customDimensions`` — it never reads the ``event_name``
    property.  Without ``event.name`` in ``customDimensions``, the Foundry
    Classic Tracing blade cannot categorise events as Input vs Output.

    This processor runs **before** the batch exporter ships the record to
    App Insights, injecting ``event.name`` into the mutable
    ``BoundedAttributes`` dict so the exporter preserves it.
    """

    def on_emit(self, log_data):
        log_record = log_data.log_record
        event_name = getattr(log_record, "event_name", None)
        if event_name:
            # BoundedAttributes is mutable (immutable=False) at this stage
            log_record.attributes["event.name"] = event_name

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=None):
        return True


class _GenAISpanEnricher(SpanProcessor):
    """Ensures ``gen_ai.operation.name`` is present on every GenAI span
    created by the OpenAI SDK instrumentor.

    The Foundry Classic Tracing blade requires **both** ``gen_ai.system``
    and ``gen_ai.operation.name`` on a dependency span to classify the
    operation and display the Input / Output columns.

    Some versions of ``opentelemetry-instrumentation-openai-v2`` set
    ``gen_ai.system`` but omit ``gen_ai.operation.name``.  This processor
    fills the gap by deriving the operation from the span name's first
    word (``"chat"`` → ``"chat"``, etc.).

    The check runs in ``on_start`` where the span is still mutable.
    By this point the instrumentor has already passed attributes
    (including ``gen_ai.system``) via ``start_span(attributes={…})``.
    We detect GenAI spans by that attribute and avoid touching
    application-level spans (e.g. ``agent_chat_request``).
    """

    _OP_MAP = {
        "chat": "chat",
        "completion": "completion",
        "completions": "completion",
        "embeddings": "embeddings",
    }

    def on_start(self, span, parent_context=None):
        # Read the span's initial attributes (populated before on_start)
        attrs = getattr(span, "_attributes", None)
        if not attrs:
            return

        name = getattr(span, "name", "") or ""
        first_word = name.split()[0] if name else ""

        # Only enrich spans the instrumentor already tagged as GenAI
        if "gen_ai.system" not in attrs:
            # Fallback: identify by span-name pattern even if gen_ai.system
            # is set *after* on_start by the instrumentor.  The first word
            # of a GenAI span name is always the operation verb.
            if first_word not in self._OP_MAP:
                return
            # If it walks like a GenAI span, set both attributes now
            span.set_attribute("gen_ai.system", "openai")
            span.set_attribute("gen_ai.operation.name", self._OP_MAP[first_word])
            return

        # gen_ai.system is present — add gen_ai.operation.name if missing
        if "gen_ai.operation.name" not in attrs:
            op = self._OP_MAP.get(first_word)
            if op:
                span.set_attribute("gen_ai.operation.name", op)

    def on_end(self, span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=None):
        return True

# ---------------------------------------------------------------------------
# OTel Initialization (deferred to avoid gunicorn fork-thread-death)
# ---------------------------------------------------------------------------
# When gunicorn starts, it imports this module in the master process,
# which starts background threads (BatchSpanProcessor worker).  After
# os.fork(), the child worker does NOT inherit those threads → telemetry
# is silently lost.  To fix this, we wrap all OTel setup in _init_otel()
# and call it AFTER fork from gunicorn.conf.py's post_fork hook.
# ---------------------------------------------------------------------------
_otel_initialized = False


def _init_otel():
    """Initialize the OTel pipeline **manually** (fork-safe).

    Bypasses ``configure_azure_monitor()`` because the distro's
    ``BatchSpanProcessor`` fails to export after ``gunicorn`` fork
    (worker thread appears alive but flush never completes).  Using
    ``SimpleSpanProcessor`` exports synchronously on every ``span.end()``
    — no background thread required, so fork cannot break it.

    Safe to call multiple times (idempotent via ``_otel_initialized``).
    Must be called in each gunicorn worker process (see ``gunicorn.conf.py``).
    """
    import sys as _sys
    global _otel_initialized
    if _otel_initialized:
        return
    _otel_initialized = True

    cs = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not cs:
        print("[otel] APPLICATIONINSIGHTS_CONNECTION_STRING not set – telemetry disabled",
              flush=True, file=_sys.stderr)
        return

    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
        from opentelemetry._logs import set_logger_provider
        from azure.monitor.opentelemetry.exporter import (
            AzureMonitorTraceExporter,
            AzureMonitorLogExporter,
        )
    except Exception as exc:
        print(f"[otel] import error: {exc}", flush=True, file=_sys.stderr)
        return

    svc = os.getenv(
        "OTEL_SERVICE_NAME",
        os.getenv("AZURE_AI_PROJECT_NAME", "grc-agent"),
    )
    resource = Resource.create({"service.name": svc})

    # ── Trace pipeline (spans → App Insights dependencies / requests) ──
    tp = TracerProvider(resource=resource)
    tp.add_span_processor(_GenAISpanEnricher())
    tp.add_span_processor(
        SimpleSpanProcessor(AzureMonitorTraceExporter(connection_string=cs))
    )
    trace.set_tracer_provider(tp)

    # ── Log / Event pipeline (GenAI events → App Insights traces) ──────
    lp = LoggerProvider(resource=resource)
    lp.add_log_record_processor(_EventNameInjector())
    lp.add_log_record_processor(
        SimpleLogRecordProcessor(AzureMonitorLogExporter(connection_string=cs))
    )
    set_logger_provider(lp)

    print(f"[otel] pipeline ready (PID={os.getpid()}, service.name={svc})",
          flush=True, file=_sys.stderr)

    # ── Instrument OpenAI SDK for GenAI tracing ────────────────────────
    try:
        from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
        OpenAIInstrumentor().instrument()
    except ImportError:
        pass  # Assistants API is traced manually in agent.py

# Get a tracer for custom spans (works even before _init_otel; returns NoOp tracer)
tracer = trace.get_tracer(__name__)

# Set up a named logger that funnels into App Insights
logger = logging.getLogger("grc-agent")
logger.setLevel(logging.INFO)

# Create Flask app
app = Flask(__name__)
CORS(app)


def _instrument_flask():
    """Instrument the Flask app for request telemetry.

    Called after ``_init_otel()`` so the TracerProvider is ready.
    """
    FlaskInstrumentor().instrument_app(app)


# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'md', 'json', 'csv', 'xml', 'html', 'py', 'js', 'ts', 'yaml', 'yml'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Store uploaded file contexts (session-based, in production use proper session storage)
uploaded_file_contexts = {}

# Global agent instance
chat_agent = None

# Store thread IDs per session (Agent Service uses threads, not AgentSession)
session_threads: dict[str, str] = {}


def _get_or_create_thread(session_id: str | None) -> tuple[str, str | None]:
    """Get an existing thread for a session or return (new_session_id, None).

    Returns:
        (session_id, thread_id) — thread_id is None when a new session is created
        and the thread will be created lazily on first chat via agent.chat().
    """
    import uuid

    if session_id and session_id in session_threads:
        return session_id, session_threads[session_id]

    # New session — thread will be created on first chat
    sid = session_id or str(uuid.uuid4())
    return sid, None


def get_agent():
    """Get or create the chat agent instance"""
    global chat_agent
    if chat_agent is None:
        chat_agent = ChatBotAgent()
    return chat_agent


@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handle chat messages from the web UI

    Expects JSON: {"message": "user message", "session_id": "optional", "file_ids": ["optional file ids"]}
    Returns JSON: {"response": "agent response", "session_id": "...", "success": true/false}
    """
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400

        user_message = data['message'].strip()

        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Empty message'
            }), 400

        # Get or create session / thread for conversation continuity
        session_id, thread_id = _get_or_create_thread(data.get('session_id'))

        # Get any attached file contexts
        file_ids = data.get('file_ids', [])
        attachment_context = ""

        if file_ids:
            attachment_texts = []
            for file_id in file_ids:
                if file_id in uploaded_file_contexts:
                    file_data = uploaded_file_contexts[file_id]
                    attachment_texts.append(
                        f"\n--- Attached File: {file_data['filename']} ---\n{file_data['content']}\n--- End of {file_data['filename']} ---\n"
                    )

            if attachment_texts:
                attachment_context = "\n\n[USER ATTACHMENTS - Use these as additional context for your response:]\n" + "\n".join(attachment_texts)

        # Combine user message with attachment context
        full_message = user_message
        if attachment_context:
            full_message = user_message + attachment_context

        # Get the agent
        agent = get_agent()

        # Run the chat in an async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Initialize agent if needed
            if agent.agent is None:
                loop.run_until_complete(agent.initialize())

            # Get response — wrapped in a custom span for App Insights
            start_time = time.time()
            with tracer.start_as_current_span("agent_chat_request") as span:
                span.set_attribute("chat.message_length", len(full_message))
                span.set_attribute("chat.has_attachments", bool(file_ids))
                span.set_attribute("chat.session_id", session_id)

                response, returned_thread_id = loop.run_until_complete(
                    agent.chat(full_message, thread_id=thread_id)
                )

                # Remember the thread for this session
                if returned_thread_id:
                    session_threads[session_id] = returned_thread_id

                elapsed = time.time() - start_time
                span.set_attribute("chat.response_length", len(response))
                span.set_attribute("chat.duration_seconds", round(elapsed, 3))

                logger.info(
                    "Chat completed",
                    extra={
                        "custom_dimensions": {
                            "message_length": len(full_message),
                            "response_length": len(response),
                            "duration_seconds": round(elapsed, 3),
                            "has_attachments": bool(file_ids),
                        }
                    },
                )

            return jsonify({
                'success': True,
                'response': response,
                'session_id': session_id
            })

        finally:
            loop.close()

    except Exception as e:
        logger.exception("Error in chat endpoint: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    Handle streaming chat messages from the web UI

    Expects JSON: {"message": "user message", "session_id": "optional", "file_ids": ["optional file ids"]}
    Returns: Server-Sent Events stream
    """
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'No message provided'
            }), 400

        user_message = data['message'].strip()

        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Empty message'
            }), 400

        # Get or create session / thread for conversation continuity
        session_id, thread_id = _get_or_create_thread(data.get('session_id'))

        # Get any attached file contexts
        file_ids = data.get('file_ids', [])
        attachment_context = ""

        if file_ids:
            attachment_texts = []
            for file_id in file_ids:
                if file_id in uploaded_file_contexts:
                    file_data = uploaded_file_contexts[file_id]
                    attachment_texts.append(
                        f"\n--- Attached File: {file_data['filename']} ---\n{file_data['content']}\n--- End of {file_data['filename']} ---\n"
                    )

            if attachment_texts:
                attachment_context = "\n\n[USER ATTACHMENTS - Use these as additional context for your response:]\n" + "\n".join(attachment_texts)

        # Combine user message with attachment context
        full_message = user_message
        if attachment_context:
            full_message = user_message + attachment_context

        def generate():
            """Generator function for streaming response"""
            nonlocal thread_id
            agent = get_agent()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Initialize agent if needed
                if agent.agent is None:
                    loop.run_until_complete(agent.initialize())

                # Collect all chunks from the async generator
                async def collect_chunks():
                    nonlocal thread_id
                    chunks = []
                    async for chunk, tid in agent.chat_stream(full_message, thread_id=thread_id):
                        thread_id = tid
                        chunks.append(chunk)
                    return chunks

                # Get all chunks
                chunks = loop.run_until_complete(collect_chunks())

                # Remember the thread for this session
                if thread_id:
                    session_threads[session_id] = thread_id

                # Yield each chunk
                for chunk in chunks:
                    yield f"data: {chunk}\n\n"

            except Exception as e:
                yield f"data: Error: {str(e)}\n\n"
            finally:
                loop.close()

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        logger.exception("Error in streaming chat endpoint: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history for a session from the Azure OpenAI thread"""
    session_id = request.args.get('session_id', '')
    thread_id = session_threads.get(session_id)

    if not thread_id:
        return jsonify({
            'success': True,
            'history': [],
            'session_id': session_id
        })

    try:
        agent = get_agent()
        if agent.client is None:
            return jsonify({'success': True, 'history': [], 'session_id': session_id})

        messages = agent.client.beta.threads.messages.list(
            thread_id=thread_id,
            order="asc",
            limit=100,
        )

        history = []
        for msg in messages.data:
            text_parts = []
            for block in msg.content:
                if block.type == "text":
                    text_parts.append(block.text.value)
            content = "\n".join(text_parts)

            # Strip attachment context that was appended to user messages
            if msg.role == "user" and "\n\n[USER ATTACHMENTS" in content:
                content = content.split("\n\n[USER ATTACHMENTS")[0]

            history.append({'role': msg.role, 'content': content})

        return jsonify({
            'success': True,
            'history': history,
            'session_id': session_id
        })

    except Exception as e:
        logger.exception("Error fetching thread history: %s", e)
        return jsonify({
            'success': True,
            'history': [],
            'session_id': session_id
        })


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear conversation history by deleting the Azure OpenAI thread"""
    data = request.get_json() or {}
    session_id = data.get('session_id', '')

    thread_id = session_threads.pop(session_id, None)

    # Best-effort delete the thread from Azure OpenAI
    if thread_id:
        try:
            agent = get_agent()
            if agent.client is not None:
                agent.client.beta.threads.delete(thread_id=thread_id)
        except Exception as e:
            logger.warning("Could not delete thread %s: %s", thread_id, e)

    return jsonify({
        'success': True,
        'message': 'Session cleared'
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    agent = get_agent()

    return jsonify({
        'success': True,
        'status': 'healthy',
        'agent_initialized': agent.agent is not None,
        'agent_name': agent.agent_name
    })


@app.route('/api/debug/otel', methods=['GET'])
def debug_otel():
    """Lightweight diagnostic endpoint — gated by DEBUG_OTEL env var."""
    if os.getenv("DEBUG_OTEL", "").lower() not in ("true", "1", "yes"):
        return jsonify({"error": "Set DEBUG_OTEL=true to enable this endpoint"}), 403

    provider = trace.get_tracer_provider()
    real = getattr(provider, "_real_tracer_provider", provider)
    processors = []
    msp = getattr(real, "_active_span_processor", None)
    if msp:
        for sp in getattr(msp, "_span_processors", []):
            info = {"class": type(sp).__name__}
            exporter = getattr(sp, "span_exporter", None)
            if exporter:
                info["exporter"] = type(exporter).__name__
            processors.append(info)

    flush_ok = False
    try:
        if hasattr(real, "force_flush"):
            flush_ok = real.force_flush(timeout_millis=5000)
    except Exception as e:
        flush_ok = str(e)

    return jsonify({
        "tracer_provider": type(real).__name__,
        "span_processors": processors,
        "resource_attrs": dict(real.resource.attributes) if hasattr(real, "resource") else {},
        "force_flush": flush_ok,
        "otel_initialized": _otel_initialized,
        "pid": os.getpid(),
    })


@app.route('/api/context/sources', methods=['GET'])
def get_context_sources():
    """Get available and enabled context sources"""
    agent = get_agent()

    return jsonify({
        'success': True,
        'sources': agent.context_manager.get_available_sources(),
        'enabled_count': len(agent.context_manager.context_sources)
    })


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_file(filepath, filename):
    """Extract text content from uploaded file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.exception("Error reading file %s: %s", filename, e)
        return None


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Handle file uploads for chat context grounding

    Returns JSON: {"success": true/false, "file_id": "...", "filename": "...", "content_preview": "..."}
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Secure the filename and save
        filename = secure_filename(file.filename)
        import uuid
        file_id = str(uuid.uuid4())
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
        file.save(filepath)

        # Extract text content
        content = extract_text_from_file(filepath, filename)

        if content is None:
            os.remove(filepath)
            return jsonify({
                'success': False,
                'error': 'Could not extract text from file'
            }), 400

        # Store the context
        uploaded_file_contexts[file_id] = {
            'filename': filename,
            'content': content,
            'filepath': filepath
        }

        # Create a preview (first 200 chars)
        preview = content[:200] + ('...' if len(content) > 200 else '')

        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'content_preview': preview,
            'content_length': len(content)
        })

    except Exception as e:
        logger.exception("Error uploading file: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/upload/<file_id>', methods=['DELETE'])
def remove_uploaded_file(file_id):
    """Remove an uploaded file from context"""
    try:
        if file_id in uploaded_file_contexts:
            # Remove the file from disk
            filepath = uploaded_file_contexts[file_id].get('filepath')
            if filepath and os.path.exists(filepath):
                os.remove(filepath)

            # Remove from context
            del uploaded_file_contexts[file_id]

            return jsonify({
                'success': True,
                'message': 'File removed'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/uploaded-files', methods=['GET'])
def get_uploaded_files():
    """Get list of currently uploaded files"""
    files = []
    for file_id, data in uploaded_file_contexts.items():
        files.append({
            'file_id': file_id,
            'filename': data['filename'],
            'content_length': len(data['content'])
        })

    return jsonify({
        'success': True,
        'files': files
    })


if __name__ == '__main__':
    # Local dev — no gunicorn, so initialise OTel directly.
    _init_otel()
    _instrument_flask()

    # Get Flask configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    print("=" * 60)
    print("Azure AI Agent Service Chat Bot - Web UI")
    print("=" * 60)
    print(f"Server starting on http://{host}:{port}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    app.run(host=host, port=port, debug=debug)
