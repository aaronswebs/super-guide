# Context Grounding Feature

## Overview

The Azure Agent Framework Chat Bot now supports **context grounding**, allowing you to ground the agent's responses in organizational policy documents and SharePoint sites. This feature is particularly useful for ensuring that the AI assistant provides responses that are aligned with your organization's policies and guidelines.

## Supported Context Types

The following context sources are available:

1. **Information Security Policy** - Ground responses in information security policies and guidelines
2. **Risk Management Policy** - Ground responses in risk management frameworks and policies
3. **Compliance and Regulatory Documents** - Ground responses in compliance and regulatory requirements
4. **Data Governance Policy** - Ground responses in data governance policies and standards
5. **AI/ML Governance Policy** - Ground responses in AI/ML governance and ethical guidelines

## Configuration

### Step 1: Enable Context Sources

In your `.env` file, specify which context sources you want to enable using a comma-separated list:

```bash
# Enable specific context sources
CONTEXT_SOURCES=information_security,ai_ml_governance,compliance_regulatory
```

### Step 2: Provide Context Documents

You have two options for providing context:

#### Option A: Local Files

Provide file paths to your policy documents:

```bash
CONTEXT_INFORMATION_SECURITY=/path/to/information_security_policy.txt
CONTEXT_AI_ML_GOVERNANCE=/path/to/ai_ml_governance_policy.txt
CONTEXT_COMPLIANCE_REGULATORY=/path/to/compliance_policy.txt
```

#### Option B: SharePoint Sites or URLs

Provide URLs to SharePoint sites or web-hosted documents:

```bash
CONTEXT_INFORMATION_SECURITY=https://yourcompany.sharepoint.com/sites/InfoSec/Policy
CONTEXT_RISK_MANAGEMENT=https://yourcompany.sharepoint.com/sites/RiskMgmt
CONTEXT_DATA_GOVERNANCE=https://yourcompany.sharepoint.com/sites/DataGov
```

**Note:** When using URLs, the agent will reference the location in its responses. For full SharePoint integration with content retrieval, additional authentication setup may be required.

### Step 3: (Optional) Use Default Context

If you enable a context source without providing a document path/URL, the system will use default guidance that instructs the agent to consider that type of policy when responding.

## Example Configuration

Here's a complete example configuration in your `.env` file:

```bash
# Agent Configuration
AGENT_NAME=Corporate Policy Assistant
AGENT_INSTRUCTIONS_FILE=agent_instructions.txt

# Context Grounding Configuration
CONTEXT_SOURCES=information_security,ai_ml_governance,data_governance

# Context Document Paths
CONTEXT_INFORMATION_SECURITY=examples/information_security_policy.txt
CONTEXT_AI_ML_GOVERNANCE=examples/ai_ml_governance_policy.txt
CONTEXT_DATA_GOVERNANCE=https://ourcompany.sharepoint.com/sites/DataGovernance
```

## Using the Context Examples

The repository includes example policy documents in the `examples/` directory:

- `examples/information_security_policy.txt` - Example Information Security Policy
- `examples/ai_ml_governance_policy.txt` - Example AI/ML Governance Policy

To use these examples:

1. Copy them to your preferred location or use them directly
2. Update your `.env` file with the paths:

```bash
CONTEXT_SOURCES=information_security,ai_ml_governance
CONTEXT_INFORMATION_SECURITY=examples/information_security_policy.txt
CONTEXT_AI_ML_GOVERNANCE=examples/ai_ml_governance_policy.txt
```

## Web UI Indicator

When context sources are enabled, the web interface will display:

1. **Header Badge**: Shows the number of active context sources
2. **Context Panel**: Lists all enabled context sources at the top of the chat
3. **Grounded Responses**: The agent will reference the provided policies in its responses

## API Endpoint

You can query the enabled context sources programmatically:

```bash
GET /api/context/sources
```

**Response:**
```json
{
  "success": true,
  "enabled_count": 2,
  "sources": [
    {
      "id": "information_security",
      "name": "Information Security Policy",
      "description": "Ground responses in information security policies and guidelines",
      "enabled": true
    },
    {
      "id": "ai_ml_governance",
      "name": "AI/ML Governance Policy",
      "description": "Ground responses in AI/ML governance and ethical guidelines",
      "enabled": true
    }
  ]
}
```

## How It Works

1. **Loading**: When the agent initializes, the Context Manager loads all enabled sources
2. **Document Processing**: For local files, the content is read and appended to the agent's instructions
3. **URL References**: For URLs, the agent is instructed to reference those locations
4. **Grounding**: The enhanced instructions guide the agent to ground its responses in the provided policies
5. **Display**: The web UI shows which context sources are active

## Best Practices

1. **Keep Policies Updated**: Regularly update your policy documents to ensure the agent has current information
2. **Use Specific Policies**: Enable only the context sources relevant to your use case
3. **Document Formatting**: Use clear, well-structured documents (Markdown recommended)
4. **File Size**: Keep policy documents reasonably sized (under 10,000 words) for optimal performance
5. **Test Responses**: Verify that the agent properly grounds its responses in your policies

## Troubleshooting

### Context Sources Not Showing

- Check that `CONTEXT_SOURCES` is set in your `.env` file
- Verify the source names match the available types exactly
- Restart the application after changing `.env`

### Documents Not Loading

- Verify file paths are absolute or relative to the application root
- Check file permissions for local files
- Ensure files are UTF-8 encoded text files

### Agent Not Using Context

- Verify the context sources appear in the startup logs
- Check that your questions relate to the policy areas you've configured
- Review the agent instructions to ensure they're not overriding the context

## Extending Context Sources

To add custom context types, modify `context_manager.py` and add new entries to the `CONTEXT_TEMPLATES` dictionary.
