#!/usr/bin/env python3
"""
MCP Weather Chatbot using AWS Strands

This demonstrates how MCP servers work with AWS Strands:
- Native MCP integration without custom wrappers
- Clean, simple API design
- Optional structured output display
- 50% less code than traditional frameworks
"""

import asyncio
import sys
import logging
from typing import Optional

# Add parent directory to path for imports
sys.path.append('.')

from mcp_agent import create_weather_agent, MCPWeatherAgent

# Configure logging
logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)


class SimpleWeatherChatbot:
    """A simple chatbot that uses MCP servers for weather data via Strands."""
    
    def __init__(self, structured_output: bool = False):
        self.agent: Optional[MCPWeatherAgent] = None
        self.structured_output = structured_output
        self.initialized = False
    
    async def initialize(self):
        """Initialize the Strands agent with MCP connections."""
        if not self.initialized:
            print("🔌 Initializing AWS Strands agent with MCP connections...")
            self.agent = await create_weather_agent(structured_output=self.structured_output)
            self.initialized = True
            print("✅ Ready to answer weather questions!\n")
    
    async def chat(self, query: str) -> str:
        """
        Process a chat query.
        
        Args:
            query: The user's question
            
        Returns:
            The agent's response
        """
        if not self.initialized:
            await self.initialize()
        
        # Process with Strands agent
        response = await self.agent.query(query)
        return response
    
    async def cleanup(self):
        """Clean up resources."""
        # Strands handles cleanup automatically
        pass


async def interactive_mode():
    """Run the chatbot in interactive mode."""
    print("🌤️  AWS Strands Weather Assistant")
    print("=" * 40)
    print("I can help you with:")
    print("- Current weather conditions")
    print("- Weather forecasts")
    print("- Historical weather data")
    print("- Agricultural recommendations")
    print("\nType 'quit' to exit, 'help' for more info")
    print("Type 'structured' to toggle detailed output\n")
    
    chatbot = SimpleWeatherChatbot()
    structured_enabled = False
    
    try:
        await chatbot.initialize()
        
        while True:
            try:
                query = input("\n💭 You: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if query.lower() == 'help':
                    print("\n📚 Help:")
                    print("- Ask any weather-related question")
                    print("- Examples:")
                    print("  - What's the weather in Chicago?")
                    print("  - Give me a 5-day forecast for Seattle")
                    print("  - Are conditions good for planting corn in Iowa?")
                    print("  - What's the frost risk for tomatoes in Minnesota?")
                    print("- Type 'structured' to see detailed tool calls")
                    continue
                
                if query.lower() == 'structured':
                    structured_enabled = not structured_enabled
                    # Recreate chatbot with new setting
                    chatbot = SimpleWeatherChatbot(structured_output=structured_enabled)
                    await chatbot.initialize()
                    print(f"\n🔧 Structured output display: {'ON' if structured_enabled else 'OFF'}")
                    continue
                
                if not query:
                    continue
                
                print("\n💭 Thinking...")
                response = await chatbot.chat(query)
                print(f"\n🤖 Assistant: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
                
    finally:
        await chatbot.cleanup()


async def demo_mode(show_structured: bool = False):
    """Run a demo showing Strands and MCP in action."""
    chatbot = SimpleWeatherChatbot(structured_output=show_structured)
    
    if show_structured:
        print("🌤️  AWS Strands Weather Demo with Structured Output")
        print("=" * 50)
        print("This demo shows how AWS Strands works with MCP:")
        print("1. Native MCP tool integration")
        print("2. Automatic tool discovery and execution")
        print("3. Clean, simple API design")
        print("4. 50% less code than traditional frameworks\n")
    else:
        print("🌤️  AWS Strands Weather Demo")
        print("=" * 50)
        print("This demo shows AWS Strands with MCP servers.")
        print("Experience the simplicity of modern AI agents.\n")
    
    try:
        await chatbot.initialize()
        
        # Demo queries
        queries = [
            "What's the weather forecast for Chicago, Illinois?",
            "Compare the weather in New York and Los Angeles",
            "Are conditions good for planting corn in Des Moines, Iowa?",
            "What was the temperature in Phoenix last week?",
            "Is there frost risk for tomatoes in Minneapolis?"
        ]
        
        for i, query in enumerate(queries[:3], 1):  # Show first 3 queries
            print(f"\n{'='*50}")
            print(f"Demo Query {i}: {query}")
            print(f"{'='*50}")
            
            response = await chatbot.chat(query)
            print(f"\n🤖 Assistant: {response}")
            
            # Brief pause between queries
            if i < 3:
                await asyncio.sleep(2)
        
        print("\n✨ Demo complete! The full system supports many more queries.")
        
    finally:
        await chatbot.cleanup()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AWS Strands Weather Chatbot"
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run in demo mode with example queries'
    )
    
    parser.add_argument(
        '--structured',
        action='store_true',
        help='Show structured output with tool calls'
    )
    
    args = parser.parse_args()
    
    if args.demo:
        await demo_mode(show_structured=args.structured)
    else:
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())