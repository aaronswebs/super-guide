"""
Azure OpenAI Assistants Chat Bot
Main agent implementation using Azure OpenAI Assistants API directly.

This version bypasses the Azure AI Agent Service (which requires Standard
Setup resources) and talks to the Azure OpenAI Assistants API using the
openai Python SDK + Azure AD authentication.

Supports Managed Identity authentication:
  - Uses DefaultAzureCredential → get_bearer_token_provider (works in Azure
    App Service with a System-assigned MI, and falls back to your local
    'az login' session for development).
"""

import os
import time
import json
import asyncio
from typing import Optional  # noqa: F401 – used in type hints
from pathlib import Path
from dotenv import load_dotenv
from context_manager import ContextManager

# ---------------------------------------------------------------------------
# OpenTelemetry GenAI tracing for Azure OpenAI Assistants API
# ---------------------------------------------------------------------------
# The `opentelemetry-instrumentation-openai-v2` instrumentor only covers
# `chat.completions.create` / `embeddings.create`.  The Assistants API
# (`beta.threads.runs.create_and_poll`) is NOT instrumented.  We manually
# emit GenAI spans and events so the Foundry Classic Tracing blade shows
# Input / Output columns.
# ---------------------------------------------------------------------------
from opentelemetry import trace

_genai_tracer = trace.get_tracer("opentelemetry.instrumentation.openai_v2")

# Whether to capture message content (may be sensitive in production)
_CAPTURE_CONTENT = os.environ.get(
    "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
).lower() in ("true", "1", "yes")


def _emit_genai_event(event_name: str, body: dict) -> None:
    """Emit a GenAI event as a span event on the current OTel span.

    Events (e.g. ``gen_ai.user.message``, ``gen_ai.choice``) populate the
    Input / Output columns in the Foundry Classic Tracing blade.  They
    are exported as ``traces`` table entries in App Insights with the
    ``message`` field set to the event name and ``gen_ai.event.content``
    in ``customDimensions`` containing the JSON body.
    """
    try:
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            current_span.add_event(event_name, attributes={
                "gen_ai.event.content": json.dumps(body),
            })
    except Exception:
        pass  # tracing is best-effort

# Retry settings for transient Azure OpenAI errors
_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 2  # initial delay, doubles each retry

# Load environment variables
load_dotenv()


class ChatBotAgent:
    """
    Turn-by-turn chat bot using Azure OpenAI Assistants API
    """

    def __init__(self):
        """Initialize the chat bot agent with Azure OpenAI configuration"""
        # Azure OpenAI endpoint  e.g. https://<resource>.openai.azure.com/
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-deployment")
        self.agent_name = os.getenv("AGENT_NAME", "ChatBot_Agent")
        self.instructions_file = os.getenv("AGENT_INSTRUCTIONS_FILE", "agent_instructions_placeholder.txt")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

        # Validate required configuration
        self._validate_config()

        # Load agent instructions
        self.instructions = self._load_instructions()

        # Initialize context manager for grounding
        self.context_manager = ContextManager()

        # Append context to instructions if available
        if self.context_manager.has_context():
            context_string = self.context_manager.get_context_string()
            self.instructions += context_string
            print(f"✓ Loaded {len(self.context_manager.context_sources)} context source(s) for grounding")

        # These are set during initialize()
        self.client = None   # AzureOpenAI client
        self.agent = None    # Assistant object returned by the API

    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_vars = {
            "AZURE_OPENAI_ENDPOINT": self.azure_openai_endpoint,
        }

        missing_vars = [var for var, value in required_vars.items() if not value]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please copy .env.example to .env and fill in your Azure credentials."
            )

    def _load_instructions(self) -> str:
        """Load agent instructions from file"""
        instructions_path = Path(self.instructions_file)

        if not instructions_path.exists():
            print(f"Warning: Instructions file '{self.instructions_file}' not found.")
            print("Using placeholder instructions. Please create your agent_instructions.txt file.")
            return "You are a helpful AI assistant. Provide accurate and helpful responses to user queries."

        with open(instructions_path, 'r', encoding='utf-8') as f:
            instructions = f.read().strip()

        if not instructions or instructions.startswith("# PLACEHOLDER"):
            print("Warning: Using placeholder instructions.")
            print("Please replace agent_instructions_placeholder.txt with your actual agent instructions.")
            return "You are a helpful AI assistant. Provide accurate and helpful responses to user queries."

        return instructions

    async def initialize(self):
        """Create or retrieve the assistant via Azure OpenAI Assistants API"""
        try:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            from openai import AzureOpenAI

            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )

            self.client = AzureOpenAI(
                azure_endpoint=self.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self.api_version,
            )
            print(f"✓ Connected to Azure OpenAI endpoint: {self.azure_openai_endpoint}")

            # Create the assistant
            self.agent = self.client.beta.assistants.create(
                model=self.deployment_name,
                name=self.agent_name,
                instructions=self.instructions,
            )

            print(f"✓ Assistant '{self.agent.name}' created  (id={self.agent.id})")
            print(f"✓ Using model deployment: {self.deployment_name}")

        except ImportError as e:
            print("Error: openai or azure-identity not installed properly.")
            print("Please run: pip install -r requirements.txt")
            raise
        except Exception as e:
            print(f"Error initializing agent: {e}")
            raise

    # -----------------------------------------------------------------
    # Thread helpers
    # -----------------------------------------------------------------

    def create_thread(self) -> str:
        """Create a new conversation thread and return its id."""
        thread = self.client.beta.threads.create()
        return thread.id

    def _run_thread(self, thread_id: str, message: str) -> str:
        """Add a user message to a thread, run the assistant, and return its reply.

        Includes retry logic for transient ``server_error`` responses that
        Azure OpenAI may return when rate-limited or under load.

        Emits GenAI-semantic OTel spans and events so the Foundry Classic
        Tracing blade can display Input / Output columns.
        """
        with _genai_tracer.start_as_current_span(
            f"chat {self.deployment_name}",
            attributes={
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": self.deployment_name,
            },
        ) as span:
            # ── Emit user-message event (populates "Input" column) ─────
            if _CAPTURE_CONTENT:
                _emit_genai_event("gen_ai.user.message", {
                    "role": "user",
                    "content": message,
                })

            # Add user message
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message,
            )

            last_error = None
            for attempt in range(_MAX_RETRIES):
                # Create and poll a run until completion
                run = self.client.beta.threads.runs.create_and_poll(
                    thread_id=thread_id,
                    assistant_id=self.agent.id,
                )

                if run.status == "completed":
                    # Record token usage if available
                    usage = getattr(run, "usage", None)
                    if usage:
                        input_tok = getattr(usage, "prompt_tokens", None)
                        output_tok = getattr(usage, "completion_tokens", None)
                        if input_tok is not None:
                            span.set_attribute("gen_ai.usage.input_tokens", input_tok)
                        if output_tok is not None:
                            span.set_attribute("gen_ai.usage.output_tokens", output_tok)
                    span.set_attribute("gen_ai.response.id", run.id)
                    span.set_attribute("gen_ai.response.model", self.deployment_name)
                    break

                if run.status == "failed":
                    last_error = run.last_error
                    # Retry on transient server_error
                    if last_error and getattr(last_error, "code", "") == "server_error" and attempt < _MAX_RETRIES - 1:
                        delay = _RETRY_DELAY_SECONDS * (2 ** attempt)
                        print(f"⚠ Run server_error (attempt {attempt + 1}/{_MAX_RETRIES}), retrying in {delay}s…")
                        time.sleep(delay)
                        continue
                    span.set_status(trace.StatusCode.ERROR, str(last_error))
                    raise RuntimeError(f"Assistant run failed: {last_error}")
            else:
                span.set_status(trace.StatusCode.ERROR, f"Retries exhausted: {last_error}")
                raise RuntimeError(f"Assistant run failed after {_MAX_RETRIES} retries: {last_error}")

            # Retrieve the assistant's last message from the thread
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1,
            )

            response_text = ""
            for msg in messages.data:
                if msg.role == "assistant":
                    for block in msg.content:
                        if block.type == "text":
                            response_text = block.text.value
                            break
                    break

            # ── Emit choice event (populates "Output" column) ─────────
            if _CAPTURE_CONTENT and response_text:
                _emit_genai_event("gen_ai.choice", {
                    "index": 0,
                    "message": {"role": "assistant", "content": response_text},
                })

            return response_text

    # -----------------------------------------------------------------
    # Public chat API (matches the interface expected by app.py)
    # -----------------------------------------------------------------

    async def chat(self, message: str, thread_id: str | None = None) -> tuple[str, str]:
        """
        Send a message to the agent and get a response.

        Args:
            message: User's message
            thread_id: Existing thread id for conversation continuity.
                       If None a new thread is created.

        Returns:
            Tuple of (response_text, thread_id)
        """
        if not self.agent:
            await self.initialize()

        try:
            if thread_id is None:
                thread_id = self.create_thread()

            response = self._run_thread(thread_id, message)
            return response, thread_id

        except Exception as e:
            error_msg = f"Error during chat: {e}"
            print(error_msg)
            return f"I apologize, but I encountered an error: {e}", thread_id or ""

    async def chat_stream(self, message: str, thread_id: str | None = None):
        """
        Send a message to the agent and stream the response.

        The Azure AI Agent Service supports streaming via
        ``create_and_process_run`` with ``stream=True``.  For simplicity
        we fall back to a non-streaming approach – the full response is
        fetched and then yielded as a single chunk.

        Args:
            message: User's message
            thread_id: Existing thread id for conversation continuity.

        Yields:
            Tuples of (chunk_text, thread_id)
        """
        if not self.agent:
            await self.initialize()

        try:
            if thread_id is None:
                thread_id = self.create_thread()

            # Use the streaming API
            try:
                # Add user message
                self.client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=message,
                )

                # Stream the run with retry for transient errors
                last_error = None
                for attempt in range(_MAX_RETRIES):
                    try:
                        with self.client.beta.threads.runs.stream(
                            thread_id=thread_id,
                            assistant_id=self.agent.id,
                        ) as stream:
                            for text in stream.text_deltas:
                                yield text, thread_id
                        last_error = None
                        break  # success
                    except Exception as stream_err:
                        last_error = stream_err
                        if attempt < _MAX_RETRIES - 1:
                            delay = _RETRY_DELAY_SECONDS * (2 ** attempt)
                            print(f"⚠ Stream error (attempt {attempt + 1}/{_MAX_RETRIES}), retrying in {delay}s…")
                            import time as _time
                            _time.sleep(delay)
                        else:
                            raise
            except (AttributeError, TypeError):
                # Fallback: non-streaming approach
                response = self._run_thread(thread_id, message)
                yield response, thread_id

        except Exception as e:
            error_msg = f"Error during streaming chat: {e}"
            print(error_msg)
            yield f"I apologize, but I encountered an error: {e}", thread_id or ""


async def main():
    """
    Simple command-line interface for testing the chat bot
    """
    print("=" * 60)
    print("Azure OpenAI Assistants Chat Bot")
    print("Powered by GPT-5 via Azure OpenAI Assistants API")
    print("=" * 60)
    print()

    # Create and initialize the agent
    bot = ChatBotAgent()
    await bot.initialize()

    print()
    print("Chat bot is ready! Type 'quit' or 'exit' to stop.")
    print("-" * 60)
    print()

    thread_id = None

    # Chat loop
    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye!")
                # Clean up: delete the agent from the registry
                if bot.agent and bot.client:
                    bot.client.beta.assistants.delete(assistant_id=bot.agent.id)
                    print("(Assistant deleted)")
                break

            print("Agent: ", end="", flush=True)

            async for chunk, tid in bot.chat_stream(user_input, thread_id=thread_id):
                thread_id = tid
                print(chunk, end="", flush=True)

            print()  # New line after response
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
