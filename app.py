"""
Web UI for Azure Agent Framework Chat Bot
Flask-based web interface for turn-by-turn chat
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
# AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED  – azure-core-tracing- SDK
# OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT – opentelemetry-instrumentation-openai-v2
# Both must be "true" for full prompt/completion capture across all layers.
# Set to "false" in production if prompt content is sensitive.
# ---------------------------------------------------------------------------
os.environ.setdefault("AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED", "true")
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
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor


class _GenAISpanEnricher(SpanProcessor):
    """Ensures ``gen_ai.system`` is present on every GenAI span.

    The Foundry Tracing blade filters spans with::

        customDimensions["gen_ai.system"] is not null

    Some versions of opentelemetry-instrumentation-openai-v2 set this
    attribute only on span *events* (which land in AppTraces) but NOT on the
    span itself (which lands in AppDependencies).  This processor fills the
    gap so Foundry can discover the spans.
    """

    _GENAI_SPAN_PREFIXES = ("chat ", "completion ", "embeddings ")

    def on_start(self, span, parent_context=None):  # Span is still mutable here
        name = getattr(span, "name", "") or ""
        if any(name.startswith(p) for p in self._GENAI_SPAN_PREFIXES):
            span.set_attribute("gen_ai.system", "openai")

    def on_end(self, span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=None):
        return True

_ai_connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if _ai_connection_string:
    # Explicitly set service.name so the Azure App Service resource detector
    # (which defaults to WEBSITE_SITE_NAME) does NOT override it.
    # This ensures cloud_RoleName in App Insights matches the AI Foundry
    # project name, which is required for the Tracing blade to find the spans.
    _service_name = os.getenv(
        "OTEL_SERVICE_NAME",
        os.getenv("AZURE_AI_PROJECT_NAME", "grc-agent"),
    )
    configure_azure_monitor(
        connection_string=_ai_connection_string,
        enable_live_metrics=True,
        logger_name="grc-agent",
        resource=Resource.create({"service.name": _service_name}),
    )
    # Register a custom SpanProcessor that adds gen_ai.system to GenAI
    # spans so the Foundry Tracing blade can discover them.
    _provider = trace.get_tracer_provider()
    _real = getattr(_provider, "_real_tracer_provider", _provider)
    if hasattr(_real, "add_span_processor"):
        _real.add_span_processor(_GenAISpanEnricher())
        print("  ↳ GenAI span enricher registered")
    print(f"✓ Application Insights telemetry enabled (service.name={_service_name})")
else:
    print("⚠ APPLICATIONINSIGHTS_CONNECTION_STRING not set — telemetry disabled")

# ---------------------------------------------------------------------------
# Azure AI Foundry / OpenAI SDK Tracing
# ---------------------------------------------------------------------------
# Instrument the OpenAI Python SDK so that every chat-completion call emits
# OpenTelemetry spans with GenAI semantic conventions (model, token counts,
# prompt/completion content).  These traces are exported to the Application
# Insights resource connected to the AI Foundry project, making them visible
# in the Foundry "Tracing" blade.
# ---------------------------------------------------------------------------
try:
    from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor
    OpenAIInstrumentor().instrument()
    print("✓ OpenAI SDK tracing enabled (Azure AI Foundry)")
except ImportError:
    print("⚠ opentelemetry-instrumentation-openai-v2 not installed — GenAI tracing disabled")

# Get a tracer for custom spans
tracer = trace.get_tracer(__name__)

# Set up a named logger that funnels into App Insights
logger = logging.getLogger("grc-agent")
logger.setLevel(logging.INFO)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Explicitly instrument Flask for request telemetry
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

# Store conversation history (in production, use a database)
conversation_history = []


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
    
    Expects JSON: {"message": "user message", "file_ids": ["optional file ids"]}
    Returns JSON: {"response": "agent response", "success": true/false}
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
            with tracer.start_as_current_span("chat_completion") as span:
                span.set_attribute("gen_ai.system", "openai")
                span.set_attribute("gen_ai.operation.name", "chat")
                span.set_attribute("chat.message_length", len(full_message))
                span.set_attribute("chat.has_attachments", bool(file_ids))

                response = loop.run_until_complete(agent.chat(full_message))

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
            
            # Store in conversation history
            conversation_history.append({
                'role': 'user',
                'content': user_message
            })
            conversation_history.append({
                'role': 'assistant',
                'content': response
            })
            
            return jsonify({
                'success': True,
                'response': response
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
    
    Expects JSON: {"message": "user message", "file_ids": ["optional file ids"]}
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
            agent = get_agent()
            full_response = []
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Initialize agent if needed
                if agent.agent is None:
                    loop.run_until_complete(agent.initialize())
                
                # Collect all chunks from the async generator
                async def collect_chunks():
                    chunks = []
                    async for chunk in agent.chat_stream(full_message):
                        chunks.append(chunk)
                    return chunks
                
                # Get all chunks
                chunks = loop.run_until_complete(collect_chunks())
                
                # Yield each chunk
                for chunk in chunks:
                    full_response.append(chunk)
                    yield f"data: {chunk}\n\n"
                
                # Store in conversation history
                conversation_history.append({
                    'role': 'user',
                    'content': user_message
                })
                conversation_history.append({
                    'role': 'assistant',
                    'content': ''.join(full_response)
                })
                
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
    """Get conversation history"""
    return jsonify({
        'success': True,
        'history': conversation_history
    })


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear conversation history"""
    global conversation_history
    conversation_history = []
    return jsonify({
        'success': True,
        'message': 'History cleared'
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
    ext = filename.rsplit('.', 1)[1].lower()
    
    try:
        # For text-based files, read directly
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
                'error': f'File type not allowed. Allowed types: {{", ".join(ALLOWED_EXTENSIONS)}}'
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
    # Get Flask configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    print("=" * 60)
    print("Azure Agent Framework Chat Bot - Web UI")
    print("=" * 60)
    print(f"Server starting on http://{host}:{port}")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=debug)
