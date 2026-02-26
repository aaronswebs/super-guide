# Quick Start Guide

This guide will help you get the Azure Agent Framework Chat Bot running in under 10 minutes.

## ⚡ Quick Setup (For Testing)

If you just want to test the application structure without Azure credentials:

1. **Clone and setup:**
   ```bash
   git clone https://github.com/aaronswebs/super-guide.git
   cd super-guide
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create a minimal .env file:**
   ```bash
   cp .env.example .env
   ```

3. **Important Note:** 
   The application will fail at runtime without valid Azure credentials. To actually use it, you need to:
   - Set up Azure AI Foundry
   - Deploy GPT-5
   - Add your credentials to the `.env` file

   See the full [README.md](README.md) for complete Azure setup instructions.

## 🚀 Production Setup (With Azure)

### Prerequisites Checklist
- [ ] Azure account with active subscription
- [ ] Python 3.10+ installed
- [ ] Git installed
- [ ] Text editor

### Step-by-Step Instructions

#### 1. Set Up Azure (15-20 minutes)

**A. Access Azure AI Foundry:**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Search for "AI Foundry" and create/select a project

**B. Request & Deploy GPT-5:**
   - In AI Foundry, go to Deployments → Model Catalog
   - Find GPT-5 (has a lock icon 🔒)
   - Click "Request Access" - fill out the form
   - Wait for approval email (1-3 business days)
   - Once approved: Deploy → Choose deployment name (e.g., `gpt-5-deployment`)
   - Note your endpoint URL (and API key, if using API key auth)

#### 2. Set Up the Application (5 minutes)

```bash
# Clone repository
git clone https://github.com/aaronswebs/super-guide.git
cd super-guide

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Or use your preferred editor
```

**Edit `.env` with your Azure credentials:**
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-deployment
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Authentication: "managed_identity" (default) or "api_key"
AZURE_OPENAI_AUTH_TYPE=managed_identity

# Only required when AZURE_OPENAI_AUTH_TYPE=api_key
# AZURE_OPENAI_API_KEY=your-api-key-here
```

#### 3. (Optional) Create Custom Instructions (2 minutes)

```bash
# Create your instructions file
touch agent_instructions.txt
nano agent_instructions.txt
```

Add your custom instructions:
```text
You are a helpful AI assistant.
Provide clear, accurate, and concise responses.
Be professional and friendly.
```

Or skip this step to use the default placeholder instructions.

#### 4. Run the Application (1 minute)

**Option A: Web UI (Recommended)**
```bash
python app.py
```
Then open: http://localhost:5000

**Option B: Command Line**
```bash
python agent.py
```

## ✅ Verification

Test that everything works:

### Web UI Test:
1. Open http://localhost:5000
2. Type: "Hello, can you hear me?"
3. You should get a response from GPT-5

### CLI Test:
1. Run `python agent.py`
2. At the prompt, type: "Tell me a joke"
3. You should get a response

### API Test:
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
```

## 🎯 Next Steps

1. **Customize Your Agent**: Edit `agent_instructions.txt` to define your agent's personality and behavior
2. **Explore the UI**: Try different queries and see how GPT-5 responds
3. **Read the Full Docs**: Check [README.md](README.md) for advanced configuration
4. **Build Something Cool**: Use the API to integrate with your own applications

## ❓ Common Issues

**"Missing required environment variables"**
- Make sure you created `.env` and filled in `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_DEPLOYMENT_NAME`
- `AZURE_OPENAI_API_KEY` is only required when `AZURE_OPENAI_AUTH_TYPE=api_key`

**"401 Unauthorized"**
- If using Managed Identity: ensure your identity has the **Cognitive Services OpenAI User** RBAC role; locally, ensure you're signed in via `az login`
- If using API key: double-check your API key in `.env`; some Azure policies disable key-based auth
- Ensure your Azure subscription is active

**"Deployment not found"**
- Verify the deployment name matches exactly what you set in Azure

**"Module not found"**
- Make sure you activated the virtual environment
- Run `pip install -r requirements.txt` again

## 📚 Resources

- [Full README](README.md) - Complete documentation
- [Azure Agent Framework](https://github.com/microsoft/agent-framework) - Official framework docs
- [Azure AI Foundry](https://ai.azure.com/) - Azure portal

---

Need more help? Check the [Troubleshooting section](README.md#-troubleshooting) in the README.
