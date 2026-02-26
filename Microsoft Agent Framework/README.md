# Azure Agent Framework Chat Bot

A turn-by-turn chat bot with web UI built using the [Microsoft Azure Agent Framework](https://github.com/microsoft/agent-framework), powered by GPT-5 via Azure AI Foundry.

## 🌟 Features

- **Azure Agent Framework**: Built on Microsoft's official agent framework for production-ready AI agents
- **GPT-5 Integration**: Leverages the latest GPT-5 model via Azure AI Foundry Agent Service
- **Turn-by-Turn Chat**: Interactive conversation interface with context awareness
- **Web UI**: Modern, responsive chat interface built with Flask
- **File Attachments**: Upload documents directly in the chat for contextual grounding
- **Customizable Instructions**: Support for custom agent instruction files
- **Context Grounding**: Ground agent responses in organizational policy documents and SharePoint sites
- **Async Support**: Built with async/await for optimal performance
- **Streaming Responses**: Real-time response streaming (optional)

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
- `agent-framework` - Microsoft Azure Agent Framework
- `agent-framework-azure-ai` - Azure AI integration
- `azure-identity` - Azure authentication
- `azure-ai-inference` - Azure AI inference SDK
- `flask` - Web framework
- `flask-cors` - CORS support
- `python-dotenv` - Environment variable management
- `aiohttp` - Async HTTP client

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

> **Note**: If your organization's Azure policy enforces Managed Identity (Entra ID) authentication,
> you will **not** need an API key. The application defaults to Managed Identity and acquires tokens
> automatically via `DefaultAzureCredential`. If you need to use an API key instead, copy it from
> **Keys and Endpoint** in the Azure Portal.

### Step 5: Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and replace the placeholders with your actual Azure credentials:

   ```bash
   # Required: Azure OpenAI/AI Foundry Configuration
   AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-deployment
   AZURE_OPENAI_API_VERSION=2025-04-01-preview

   # Authentication Type: "managed_identity" (default) or "api_key"
   # managed_identity uses Azure Entra ID via DefaultAzureCredential (recommended).
   # api_key uses a traditional API key (set AZURE_OPENAI_API_KEY below).
   AZURE_OPENAI_AUTH_TYPE=managed_identity

   # Azure OpenAI API Key (only required when AZURE_OPENAI_AUTH_TYPE=api_key)
   # AZURE_OPENAI_API_KEY=your-api-key-here

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

> **Managed Identity vs API Key**: Many Azure subscriptions have policies that disable API key
> authentication on Azure OpenAI resources. The default `managed_identity` mode works automatically
> in Azure App Service (using the System-assigned Managed Identity) and locally (using your
> `az login` session). Only switch to `api_key` if your environment explicitly allows API keys.

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
Azure Agent Framework Chat Bot - Web UI
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
Azure Agent Framework Chat Bot
Powered by GPT-5 via Azure AI Foundry
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
| `AZURE_OPENAI_AUTH_TYPE` | ⚪ No | Authentication mode: `managed_identity` (default) or `api_key` | `managed_identity` |
| `AZURE_OPENAI_API_KEY` | ⚠️ Conditional | Required only when `AUTH_TYPE=api_key` | `abc123...` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | ✅ Yes | Name of your GPT-5 deployment | `gpt-5-deployment` |
| `AZURE_OPENAI_API_VERSION` | ⚪ No | API version to use | `2025-04-01-preview` |
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
├── agent.py                           # Core agent implementation
├── app.py                             # Flask web application
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
Get conversation history.

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
Clear conversation history.

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

## 🐛 Troubleshooting

### Issue: "Missing required environment variables"

**Solution**: Ensure your `.env` file exists and contains all required variables:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT_NAME`
- `AZURE_OPENAI_API_KEY` (only if `AZURE_OPENAI_AUTH_TYPE=api_key`)

### Issue: "Azure Agent Framework not installed properly"

**Solution**: Reinstall dependencies:
```bash
pip uninstall agent-framework agent-framework-azure-ai
pip install -r requirements.txt
```

### Issue: "401 Unauthorized" or "403 Forbidden"

**Solutions**:
1. **Managed Identity mode** (`AZURE_OPENAI_AUTH_TYPE=managed_identity`):
   - Ensure your App Service has a **System-assigned Managed Identity** enabled
   - Verify the Managed Identity has the **Cognitive Services OpenAI User** RBAC role on the Azure OpenAI resource
   - For local development, ensure you are signed in via `az login` with an account that has the correct RBAC role
2. **API Key mode** (`AZURE_OPENAI_AUTH_TYPE=api_key`):
   - Verify your API key is correct in `.env`
   - Check that your Azure OpenAI resource allows local (key-based) authentication — some Azure policies disable this
3. Ensure your Azure subscription is active
4. Check that GPT-5 access has been approved
5. Verify the deployment name matches exactly

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

## 📚 Learn More

### Azure Agent Framework
- [Official GitHub Repository](https://github.com/microsoft/agent-framework)
- [Documentation](https://learn.microsoft.com/en-us/agent-framework/)
- [Python Quick Start](https://learn.microsoft.com/en-us/agent-framework/quickstart-python)
- [Samples and Examples](https://github.com/microsoft/Agent-Framework-Samples)

### Azure AI Foundry
- [Azure AI Foundry Portal](https://ai.azure.com/)
- [Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/)
- [GPT-5 Model Family](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/gpt-5-model-family-now-powers-azure-ai-foundry-agent-service/4454860)

### Related Technologies
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Python Async Programming](https://docs.python.org/3/library/asyncio.html)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the terms specified in the LICENSE file.

## 🙏 Acknowledgments

- Built with [Microsoft Azure Agent Framework](https://github.com/microsoft/agent-framework)
- Powered by GPT-5 via Azure AI Foundry
- UI inspired by modern chat applications

## 📞 Support

If you encounter issues:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review [Azure Agent Framework Documentation](https://learn.microsoft.com/en-us/agent-framework/)
3. Open an issue in this repository

---

**Happy Chatting! 🚀**