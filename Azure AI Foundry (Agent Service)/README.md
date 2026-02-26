# Azure OpenAI Assistants Chat Bot

A turn-by-turn chat bot with web UI powered by the [Azure OpenAI Assistants API](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/assistant) and GPT-5 via Azure AI Foundry.

## 🌟 Features

- **Azure OpenAI Assistants API**: Production-ready conversational AI using the OpenAI Assistants API on Azure
- **GPT-5 Integration**: Leverages the latest GPT-5 model deployed in Azure AI Foundry
- **Server-Side Conversation History**: Conversation threads are stored and managed by the Azure OpenAI service — no in-memory state required
- **Turn-by-Turn Chat**: Interactive conversation interface with full context awareness across messages
- **Web UI**: Modern, responsive chat interface built with Flask
- **File Attachments**: Upload documents directly in the chat for contextual grounding
- **Customizable Instructions**: Support for custom agent instruction files
- **Context Grounding**: Ground agent responses in organizational policy documents and SharePoint sites
- **Async Support**: Built with async/await for optimal performance
- **Streaming Responses**: Real-time response streaming via the Assistants streaming API
- **Managed Identity Auth**: Secure, keyless authentication via Azure Entra ID (DefaultAzureCredential)

## 📋 Prerequisites

Before you begin, ensure you have the following:

1. **Python 3.10 or higher** installed on your system
2. **Azure Account** with an active subscription
3. **Azure AI Foundry** access (with GPT-5 deployment)
4. **Git** for cloning the repository

## 🚀 Getting Started

### Step 1: Clone the Repository

```bash
git clone https://github.com/aaronswebs/super-guide.git
cd super-guide
```

### Step 2: Set Up Python Virtual Environment

Create and activate a virtual environment:

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `openai` - OpenAI Python SDK (Azure OpenAI Assistants API)
- `azure-identity` - Azure Entra ID / Managed Identity authentication
- `flask` - Web framework
- `flask-cors` - CORS support
- `python-dotenv` - Environment variable management
- `aiohttp` - Async HTTP client
- `azure-monitor-opentelemetry` - Application Insights telemetry
- `opentelemetry-instrumentation-flask` - Flask request tracing
- `opentelemetry-instrumentation-openai-v2` - GenAI span tracing

### Step 4: Set Up Azure AI Foundry and Deploy GPT-5

#### 4.1 Access Azure AI Foundry

1. Log in to the [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure AI Foundry** (or search for "AI Foundry" in the portal)
3. Create a new AI Foundry project or select an existing one

#### 4.2 Request GPT-5 Access

GPT-5 is a gated model that requires approval:

1. In Azure AI Foundry, go to **Deployments** → **Model Catalog**
2. Search for "GPT-5" in the model catalog
3. Click on the GPT-5 model (it will have a lock icon 🔒)
4. Click **Request Access** and fill out the access request form
5. Include your Azure subscription ID and use case details
6. Wait for approval (typically 1-3 business days)
7. You'll receive an email confirmation when approved

#### 4.3 Deploy GPT-5

Once approved:

1. Return to **Deployments** in Azure AI Foundry
2. Click **+ Deploy model**
3. Select **GPT-5** from the available models
4. Configure deployment settings:
   - **Deployment name**: Choose a name (e.g., `gpt-5-deployment`)
   - **Region**: Select your preferred Azure region
   - **Rate limit**: Set tokens per minute (TPM) based on your needs
5. Click **Deploy**
6. Wait for deployment to complete (takes a few minutes)

#### 4.4 Get Your Credentials

After deployment:

1. Go to your deployment details
2. Copy the following values:
   - **Endpoint URL**: `https://your-resource-name.openai.azure.com/`
   - **Deployment Name**: The name you chose during deployment

> **Note**: This application uses Managed Identity (Azure Entra ID) authentication exclusively.
> You do not need an API key. Ensure your identity (or App Service Managed Identity) has the
> **Cognitive Services OpenAI Contributor** RBAC role on the Azure OpenAI resource.

### Step 5: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and replace the placeholders with your actual Azure credentials:

   ```bash
   # Required: Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-deployment
   AZURE_OPENAI_API_VERSION=2025-01-01-preview

   # Optional: Additional Azure Details
   AZURE_SUBSCRIPTION_ID=your-subscription-id
   AZURE_RESOURCE_GROUP=your-resource-group
   AZURE_AI_PROJECT_NAME=your-project-name

   # Agent Configuration
   AGENT_NAME=ChatBot Agent
   AGENT_INSTRUCTIONS_FILE=agent_instructions.txt

   # Web Server Configuration
   FLASK_HOST=0.0.0.0
   FLASK_PORT=5000
   FLASK_DEBUG=true
   ```

> **Authentication**: This application uses Managed Identity (Azure Entra ID) exclusively via
> `DefaultAzureCredential`. In Azure App Service, enable System-assigned Managed Identity and
> grant it the **Cognitive Services OpenAI Contributor** RBAC role on your Azure OpenAI resource.
> For local development, sign in via `az login` with an account that has the same RBAC role.

### Step 6: Create Your Agent Instructions File

The chat bot uses an instructions file to define its behavior and personality.

**Option A: Use the placeholder (for testing)**

The project includes `agent_instructions_placeholder.txt` with basic instructions. This will work but provides generic responses.

**Option B: Create your own instructions file (recommended)**

Create a file named `agent_instructions.txt` in the project root:

```bash
touch agent_instructions.txt
```

Then edit it with your custom instructions:

```text
You are a helpful AI assistant specialized in [your domain].

Your responsibilities:
- Provide accurate and detailed information about [topic]
- Always maintain a professional and friendly tone
- When uncertain, acknowledge limitations rather than guessing
- Cite sources when providing factual information
- Ask clarifying questions when needed

Guidelines:
- Keep responses concise but comprehensive
- Use examples to illustrate complex concepts
- Adapt your language to the user's level of expertise
- Prioritize user safety and ethical considerations

Example interactions:
[Add examples of desired behavior]
```

**Note**: The application will automatically load your `agent_instructions.txt` file if it exists, otherwise it will use the placeholder.

### Step 6a: (Optional) Configure Context Grounding

You can ground your agent's responses in organizational policy documents or SharePoint sites. This is useful for ensuring responses align with your organization's policies.

**Quick Setup:**

1. In your `.env` file, add context sources:
   ```bash
   CONTEXT_SOURCES=information_security,ai_ml_governance
   CONTEXT_INFORMATION_SECURITY=examples/information_security_policy.txt
   CONTEXT_AI_ML_GOVERNANCE=examples/ai_ml_governance_policy.txt
   ```

2. The repository includes example policy documents in the `examples/` directory you can use or customize.

**For complete details**, see [CONTEXT_GROUNDING.md](CONTEXT_GROUNDING.md) for:
- All available context types
- How to use SharePoint sites
- Configuration examples
- Best practices

### Step 6b: Using File Attachments in Chat

The web UI supports uploading files directly in the chat interface for additional context grounding. This allows users to attach documents that the agent can reference when responding.

**Supported File Types:**
- Text files: `.txt`, `.md`
- Data files: `.json`, `.csv`, `.xml`, `.yaml`, `.yml`
- Web files: `.html`
- Code files: `.py`, `.js`, `.ts`

**How to Use:**
1. Click the 📎 attachment button next to the message input
2. Select one or more files (max 5MB each)
3. Attached files will appear above the input field
4. Type your message and send - the agent will have access to the file contents
5. Files can be removed before sending by clicking the × button

**Example Use Cases:**
- Upload a policy document and ask questions about it
- Share a code file for review or debugging assistance
- Attach configuration files for analysis
- Include error logs for troubleshooting

### Step 7: Run the Application

#### Option A: Web UI (Recommended)

Start the web server:

```bash
python app.py
```

You should see:
```
============================================================
Azure OpenAI Assistants Chat Bot - Web UI
============================================================
Server starting on http://0.0.0.0:5000
Press Ctrl+C to stop
============================================================
```

Open your browser and navigate to:
```
http://localhost:5000
```

You'll see a modern chat interface where you can interact with your GPT-5 powered agent!

#### Option B: Command Line Interface

For testing or development, you can use the CLI:

```bash
python agent.py
```

This provides a simple command-line chat interface:
```
============================================================
Azure OpenAI Assistants Chat Bot
Powered by GPT-5 via Azure OpenAI Assistants API
============================================================

✓ Agent 'ChatBot Agent' initialized successfully
✓ Using GPT-5 deployment: gpt-5-deployment

Chat bot is ready! Type 'quit' or 'exit' to stop.
------------------------------------------------------------

You: 
```

## 🔧 Configuration Reference

### Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | ✅ Yes | Your Azure OpenAI endpoint URL | `https://my-resource.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | ✅ Yes | Name of your GPT-5 deployment | `gpt-5-deployment` |
| `AZURE_OPENAI_API_VERSION` | ⚪ No | API version to use | `2025-01-01-preview` |
| `AZURE_SUBSCRIPTION_ID` | ⚪ No | Your Azure subscription ID | `12345678-1234-...` |
| `AZURE_RESOURCE_GROUP` | ⚪ No | Your Azure resource group name | `my-resource-group` |
| `AZURE_AI_PROJECT_NAME` | ⚪ No | Your AI Foundry project name | `my-ai-project` |
| `AGENT_NAME` | ⚪ No | Display name for your agent | `ChatBot Agent` |
| `AGENT_INSTRUCTIONS_FILE` | ⚪ No | Path to instructions file | `agent_instructions.txt` |
| `CONTEXT_SOURCES` | ⚪ No | Comma-separated context sources to enable | `information_security,ai_ml_governance` |
| `CONTEXT_INFORMATION_SECURITY` | ⚪ No | Path/URL to Information Security policy | `examples/info_sec_policy.txt` |
| `CONTEXT_RISK_MANAGEMENT` | ⚪ No | Path/URL to Risk Management policy | `https://sharepoint.com/...` |
| `CONTEXT_COMPLIANCE_REGULATORY` | ⚪ No | Path/URL to Compliance documents | `examples/compliance.txt` |
| `CONTEXT_DATA_GOVERNANCE` | ⚪ No | Path/URL to Data Governance policy | `examples/data_gov.txt` |
| `CONTEXT_AI_ML_GOVERNANCE` | ⚪ No | Path/URL to AI/ML Governance policy | `examples/ai_ml_policy.txt` |
| `FLASK_HOST` | ⚪ No | Web server host | `0.0.0.0` |
| `FLASK_PORT` | ⚪ No | Web server port | `5000` |
| `FLASK_DEBUG` | ⚪ No | Enable Flask debug mode | `true` or `false` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | ⚪ No | Application Insights connection string for telemetry | `InstrumentationKey=...` |
| `OTEL_SERVICE_NAME` | ⚪ No | Service name shown in OTel traces | `my-ai-project` |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | ⚪ No | Capture full message content in GenAI trace events | `true` or `false` |
| `DEBUG_OTEL` | ⚪ No | Enable the `/api/debug/otel` diagnostic endpoint | `true` or `false` |

### Agent Instructions File Format

Your `agent_instructions.txt` should be a plain text file containing:

1. **Role Definition**: What is the agent's purpose?
2. **Behavioral Guidelines**: How should it interact?
3. **Constraints**: What should it avoid?
4. **Examples**: Sample interactions (optional)

Example structure:
```text
[Role]
You are an expert in...

[Guidelines]
- Always...
- Never...
- When...

[Constraints]
- Do not...
- Ensure...

[Examples]
User: "..."
Assistant: "..."
```

## 📁 Project Structure

```
super-guide/
├── agent.py                           # Core agent implementation (Assistants API + GenAI tracing)
├── app.py                             # Flask web application + OTel pipeline setup
├── gunicorn.conf.py                   # Gunicorn config with post_fork OTel hook
├── context_manager.py                 # Context grounding manager
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── .gitignore                        # Git ignore rules
├── agent_instructions_placeholder.txt # Placeholder instructions
├── agent_instructions.txt            # Your custom instructions (create this)
├── examples/                          # Example policy documents
│   ├── information_security_policy.txt
│   └── ai_ml_governance_policy.txt
├── templates/
│   └── index.html                    # Web UI template
├── README.md                         # This file
└── CONTEXT_GROUNDING.md              # Context grounding documentation
```

## 🔍 API Endpoints

The web application provides the following REST API endpoints:

### `POST /api/chat`
Send a message and get a response.

**Request:**
```json
{
  "message": "What is Azure AI Foundry?"
}
```

**Response:**
```json
{
  "success": true,
  "response": "Azure AI Foundry is..."
}
```

### `POST /api/chat/stream`
Send a message and stream the response (Server-Sent Events).

### `GET /api/history`
Get conversation history from the Azure OpenAI thread. Messages are fetched directly from the server-side thread — no local state is stored.

**Response:**
```json
{
  "success": true,
  "history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"}
  ]
}
```

### `POST /api/history/clear`
Clear conversation history by deleting the Azure OpenAI thread and starting a fresh session.

### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
  "success": true,
  "status": "healthy",
  "agent_initialized": true,
  "agent_name": "ChatBot Agent"
}
```

### `GET /api/context/sources`
Get available and enabled context sources for grounding.

**Response:**
```json
{
  "success": true,
  "enabled_count": 2,
  "sources": [
    {
      "id": "information_security",
      "name": "Information Security Policy",
      "description": "Ground responses in information security policies",
      "enabled": true
    },
    {
      "id": "ai_ml_governance",
      "name": "AI/ML Governance Policy",
      "description": "Ground responses in AI/ML governance",
      "enabled": true
    }
  ]
}
```

## 🧪 Testing

### Test the CLI Interface

```bash
python agent.py
```

Try asking questions like:
- "What is artificial intelligence?"
- "Explain quantum computing"
- "Tell me a joke"

### Test the Web UI

1. Start the server: `python app.py`
2. Open browser: `http://localhost:5000`
3. Send test messages through the chat interface
4. Verify responses are working correctly

### Test API Endpoints

Using curl:

```bash
# Test health endpoint
curl http://localhost:5000/api/health

# Test chat endpoint
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

# Get conversation history
curl http://localhost:5000/api/history
```

## � Tracing & Telemetry

This application sends OpenTelemetry traces and GenAI spans to Azure Application Insights, enabling end-to-end visibility in the **Azure AI Foundry Tracing** blade.

### Architecture

The telemetry pipeline is built manually rather than using `configure_azure_monitor()`. This is necessary because the app runs under **Gunicorn** on Azure App Service — Gunicorn's `fork()` model kills the background threads used by `BatchSpanProcessor`, preventing telemetry from ever being exported.

**Solution**: A manual pipeline using `SimpleSpanProcessor` (synchronous, fork-safe) is initialised after the Gunicorn fork via a `post_fork` hook in `gunicorn.conf.py`.

Key components:

| File | Responsibility |
|------|----------------|
| `gunicorn.conf.py` | Defines `post_fork` hook that calls `_init_otel()` and `_instrument_flask()` after each worker forks |
| `app.py` → `_init_otel()` | Builds the OTel pipeline: `TracerProvider` + `SimpleSpanProcessor` → `AzureMonitorTraceExporter`, `LoggerProvider` + `SimpleLogRecordProcessor` → `AzureMonitorLogExporter`. Instruments the OpenAI SDK. |
| `app.py` → `_GenAISpanEnricher` | A `SpanProcessor` that injects `gen_ai.operation.name` into GenAI spans (required by the Foundry tracing blade) |
| `agent.py` → `_run_thread()` | Creates manual GenAI spans for each Assistants API call with semantic-convention attributes and events |

### Why Manual GenAI Spans?

The `opentelemetry-instrumentation-openai-v2` package only instruments the OpenAI `chat.completions.create` and `embeddings.create` methods. It does **not** cover the Assistants API (`client.beta.threads.runs.create_and_poll`). Therefore, `agent.py` creates GenAI spans manually with:

- **Span name**: `chat {deployment_name}` (e.g., `chat gpt-5-deployment`)
- **Attributes**: `gen_ai.system`, `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.response.id`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- **Events**: `gen_ai.user.message` (user prompt) and `gen_ai.choice` (assistant response) — these populate the **Input** and **Output** columns in the Foundry tracing blade

### Environment Variables for Telemetry

| Variable | Required | Description |
|----------|----------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | ✅ Yes | Connection string for your Application Insights resource |
| `OTEL_SERVICE_NAME` | ⚪ No | Service name shown in traces (defaults to the AI Foundry project name) |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | ⚪ No | Set to `true` to capture full user/assistant message content in trace events |
| `DEBUG_OTEL` | ⚪ No | Set to `true` to enable the `/api/debug/otel` diagnostic endpoint |

### Viewing Traces

1. Open the [Azure AI Foundry portal](https://ai.azure.com/)
2. Navigate to your project → **Tracing**
3. GenAI traces appear as `chat gpt-5-deployment` with Input/Output columns populated
4. Click a trace to see the full span tree including Flask request → GenAI span → token usage

## �🐛 Troubleshooting

### Issue: "Missing required environment variables"

**Solution**: Ensure your `.env` file exists and contains all required variables:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT_NAME`

### Issue: "openai not installed properly"

**Solution**: Reinstall dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "401 Unauthorized" or "403 Forbidden"

**Solutions**:
1. Ensure your App Service has a **System-assigned Managed Identity** enabled
2. Verify the Managed Identity has the **Cognitive Services OpenAI Contributor** RBAC role on the Azure OpenAI resource
3. For local development, ensure you are signed in via `az login` with an account that has the same RBAC role
4. Ensure your Azure subscription is active
5. Check that GPT-5 access has been approved
6. Verify the deployment name matches exactly

### Issue: "Deployment not found"

**Solution**: Double-check your deployment name in Azure AI Foundry matches the name in your `.env` file.

### Issue: "Rate limit exceeded"

**Solution**: You've exceeded your configured tokens per minute (TPM) limit. Either:
1. Wait for the rate limit to reset
2. Increase your TPM limit in Azure AI Foundry deployment settings

### Issue: Web UI doesn't load

**Solutions**:
1. Verify Flask is running: Check console for startup messages
2. Check the correct URL: Should be `http://localhost:5000`
3. Check firewall: Ensure port 5000 is not blocked
4. Try a different port: Change `FLASK_PORT` in `.env`

### Issue: Agent gives generic responses

**Solution**: Replace `agent_instructions_placeholder.txt` with your custom `agent_instructions.txt` file containing specific instructions for your use case.

### Issue: No traces appearing in AI Foundry Tracing blade

**Solutions**:
1. Verify `APPLICATIONINSIGHTS_CONNECTION_STRING` is set correctly in App Service configuration
2. Ensure the Application Insights resource is linked to your AI Foundry project
3. Enable the diagnostic endpoint by setting `DEBUG_OTEL=true` and check `/api/debug/otel` for pipeline status
4. Confirm `force_flush` returns `true` in the debug output — if `false`, the OTel pipeline failed to initialise

### Issue: Traces appear but Input/Output columns show `--`

**Solutions**:
1. Set `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true` in your App Service configuration
2. Verify that `gen_ai.user.message` and `gen_ai.choice` events are present in the Application Insights `traces` table
3. Ensure `OTEL_SERVICE_NAME` matches your AI Foundry project name (e.g., `aiproj-grc-agent-grc02`)

## 📚 Learn More

### Azure OpenAI Assistants API
- [Assistants API Overview](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/assistant)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)

### Azure AI Foundry
- [Azure AI Foundry Portal](https://ai.azure.com/)
- [Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- [GPT-5 Model Family](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/gpt-5-model-family-now-powers-azure-ai-foundry-agent-service/4454860)

### Related Technologies
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Azure Identity / DefaultAzureCredential](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential)
- [Python Async Programming](https://docs.python.org/3/library/asyncio.html)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the terms specified in the LICENSE file.

## 🙏 Acknowledgments

- Built with the [Azure OpenAI Assistants API](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/assistant) and the [OpenAI Python SDK](https://github.com/openai/openai-python)
- Powered by GPT-5 via Azure AI Foundry
- UI inspired by modern chat applications

## 📞 Support

If you encounter issues:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review [Azure OpenAI Assistants API Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/assistant)
3. Open an issue in this repository

---

**Happy Chatting! 🚀**