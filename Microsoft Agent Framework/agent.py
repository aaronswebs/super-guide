"""
Azure Agent Framework Chat Bot
Main agent implementation using Azure AI Foundry and GPT-5

Supports two authentication modes:
  - managed_identity: Uses Azure Managed Identity (Entra ID) via DefaultAzureCredential.
    Works automatically in Azure App Service with a System-assigned Managed Identity,
    and falls back to your local 'az login' session for development.
  - api_key: Uses a traditional Azure OpenAI API key (for local development only).

Set AZURE_OPENAI_AUTH_TYPE in your .env file to choose the mode (default: managed_identity).
"""

import os
import asyncio
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from context_manager import ContextManager
from agent_framework import AgentSession

# Load environment variables
load_dotenv()


class ChatBotAgent:
    """
    Turn-by-turn chat bot using Azure Agent Framework and GPT-5
    """
    
    def __init__(self):
        """Initialize the chat bot agent with Azure AI configuration"""
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")
        self.agent_name = os.getenv("AGENT_NAME", "ChatBot_Agent")
        self.instructions_file = os.getenv("AGENT_INSTRUCTIONS_FILE", "agent_instructions_placeholder.txt")
        
        # Authentication mode: "managed_identity" (default) or "api_key"
        self.auth_type = os.getenv("AZURE_OPENAI_AUTH_TYPE", "managed_identity").lower().strip()
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY") if self.auth_type == "api_key" else None
        self.credential = None  # Set during initialize() for managed_identity
        
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
        
        # Initialize the agent (will be set up in _initialize_agent)
        self.agent = None
        self.chat_client = None
        
    def _validate_config(self):
        """Validate that all required configuration is present"""
        # These are always required regardless of auth type
        required_vars = {
            "AZURE_OPENAI_ENDPOINT": self.endpoint,
            "AZURE_OPENAI_DEPLOYMENT_NAME": self.deployment_name
        }
        
        # API key is only required when using api_key auth type
        if self.auth_type == "api_key":
            required_vars["AZURE_OPENAI_API_KEY"] = self.api_key
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please copy .env.example to .env and fill in your Azure credentials."
            )
        
        if self.auth_type not in ("managed_identity", "api_key"):
            raise ValueError(
                f"Invalid AZURE_OPENAI_AUTH_TYPE: '{self.auth_type}'. "
                f"Must be 'managed_identity' or 'api_key'."
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
        """Initialize the Azure Agent Framework agent"""
        try:
            # Import Azure Agent Framework components
            from agent_framework import Agent
            from agent_framework.azure import AzureOpenAIChatClient
            
            # Create Azure OpenAI chat client based on auth type
            if self.auth_type == "managed_identity":
                from azure.identity import DefaultAzureCredential
                
                self.credential = DefaultAzureCredential()
                self.chat_client = AzureOpenAIChatClient(
                    endpoint=self.endpoint,
                    credential=self.credential,
                    deployment_name=self.deployment_name,
                    api_version=self.api_version
                )
                print(f"✓ Using Managed Identity (Entra ID) authentication")
            else:
                self.chat_client = AzureOpenAIChatClient(
                    endpoint=self.endpoint,
                    api_key=self.api_key,
                    deployment_name=self.deployment_name,
                    api_version=self.api_version
                )
                print(f"✓ Using API key authentication")
            
            # Create the chat agent
            self.agent = Agent(
                client=self.chat_client,
                instructions=self.instructions,
                name=self.agent_name
            )
            
            print(f"✓ Agent '{self.agent_name}' initialized successfully")
            print(f"✓ Using GPT-5 deployment: {self.deployment_name}")
            
        except ImportError as e:
            print(f"Error: Azure Agent Framework not installed properly.")
            print(f"Please run: pip install -r requirements.txt")
            raise
        except Exception as e:
            print(f"Error initializing agent: {e}")
            raise
    
    async def chat(self, message: str, session: AgentSession | None = None) -> str:
        """
        Send a message to the agent and get a response
        
        Args:
            message: User's message
            session: AgentSession for conversation history retention
            
        Returns:
            Agent's response
        """
        if not self.agent:
            await self.initialize()
        
        try:
            # Run the agent with the user's message and session for history
            result = await self.agent.run(message, session=session)
            
            # Extract the response text
            if hasattr(result, 'text'):
                return result.text
            elif isinstance(result, str):
                return result
            else:
                return str(result)
                
        except Exception as e:
            error_msg = f"Error during chat: {e}"
            print(error_msg)
            return f"I apologize, but I encountered an error: {e}"
    
    async def chat_stream(self, message: str, session: AgentSession | None = None):
        """
        Send a message to the agent and stream the response
        
        Args:
            message: User's message
            session: AgentSession for conversation history retention
            
        Yields:
            Chunks of the agent's response
        """
        if not self.agent:
            await self.initialize()
        
        try:
            # Run the agent with streaming enabled and session for history
            async for chunk in self.agent.run(message, stream=True, session=session):
                if hasattr(chunk, 'text'):
                    yield chunk.text
                else:
                    yield str(chunk)
                    
        except Exception as e:
            error_msg = f"Error during streaming chat: {e}"
            print(error_msg)
            yield f"I apologize, but I encountered an error: {e}"


async def main():
    """
    Simple command-line interface for testing the chat bot
    """
    print("=" * 60)
    print("Azure Agent Framework Chat Bot")
    print("Powered by GPT-5 via Azure AI Foundry")
    print("=" * 60)
    print()
    
    # Create and initialize the agent
    bot = ChatBotAgent()
    await bot.initialize()
    
    print()
    print("Chat bot is ready! Type 'quit' or 'exit' to stop.")
    print("-" * 60)
    print()
    
    # Chat loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye!")
                break
            
            print("Agent: ", end="", flush=True)
            
            # Use streaming for better user experience
            async for chunk in bot.chat_stream(user_input):
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
