"""
Azure Agent Framework Chat Bot
Main agent implementation using Azure AI Foundry and GPT-5
"""

import os
import asyncio
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ChatBotAgent:
    """
    Turn-by-turn chat bot using Azure Agent Framework and GPT-5
    """
    
    def __init__(self):
        """Initialize the chat bot agent with Azure AI configuration"""
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-06-01-preview")
        self.agent_name = os.getenv("AGENT_NAME", "ChatBot Agent")
        self.instructions_file = os.getenv("AGENT_INSTRUCTIONS_FILE", "agent_instructions_placeholder.txt")
        
        # Validate required configuration
        self._validate_config()
        
        # Load agent instructions
        self.instructions = self._load_instructions()
        
        # Initialize the agent (will be set up in _initialize_agent)
        self.agent = None
        self.chat_client = None
        
    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_vars = {
            "AZURE_OPENAI_ENDPOINT": self.endpoint,
            "AZURE_OPENAI_API_KEY": self.api_key,
            "AZURE_OPENAI_DEPLOYMENT_NAME": self.deployment_name
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
        """Initialize the Azure Agent Framework agent"""
        try:
            # Import Azure Agent Framework components
            from agent_framework import ChatAgent
            from agent_framework.azure import AzureOpenAIChatClient
            
            # Create Azure OpenAI chat client
            self.chat_client = AzureOpenAIChatClient(
                endpoint=self.endpoint,
                api_key=self.api_key,
                deployment_name=self.deployment_name,
                api_version=self.api_version
            )
            
            # Create the chat agent
            self.agent = ChatAgent(
                name=self.agent_name,
                chat_client=self.chat_client,
                instructions=self.instructions
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
    
    async def chat(self, message: str) -> str:
        """
        Send a message to the agent and get a response
        
        Args:
            message: User's message
            
        Returns:
            Agent's response
        """
        if not self.agent:
            await self.initialize()
        
        try:
            # Run the agent with the user's message
            result = await self.agent.run(message)
            
            # Extract the response text
            if hasattr(result, 'content'):
                return result.content
            elif isinstance(result, str):
                return result
            else:
                return str(result)
                
        except Exception as e:
            error_msg = f"Error during chat: {e}"
            print(error_msg)
            return f"I apologize, but I encountered an error: {e}"
    
    async def chat_stream(self, message: str):
        """
        Send a message to the agent and stream the response
        
        Args:
            message: User's message
            
        Yields:
            Chunks of the agent's response
        """
        if not self.agent:
            await self.initialize()
        
        try:
            # Run the agent with streaming enabled
            async for chunk in self.agent.run_stream(message):
                if hasattr(chunk, 'content'):
                    yield chunk.content
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
