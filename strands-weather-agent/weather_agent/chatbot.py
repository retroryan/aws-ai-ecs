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

try:
    from .mcp_agent import create_weather_agent, MCPWeatherAgent
except ImportError:
    from mcp_agent import create_weather_agent, MCPWeatherAgent

# Configure logging
logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)


class SimpleWeatherChatbot:
    """A simple chatbot that uses MCP servers for weather data via Strands."""
    
    def __init__(self, debug_logging: bool = False):
        self.agent: Optional[MCPWeatherAgent] = None
        self.debug_logging = debug_logging
        self.initialized = False
    
    async def initialize(self):
        """Initialize the Strands agent with MCP connections."""
        if not self.initialized:
            print("🔌 Initializing AWS Strands agent with MCP connections...")
            self.agent = await create_weather_agent(debug_logging=self.debug_logging)
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
    print("Type 'debug' to toggle detailed logging\n")
    
    chatbot = SimpleWeatherChatbot()
    debug_enabled = False
    
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
                    print("- Type 'debug' to see detailed tool calls")
                    continue
                
                if query.lower() == 'debug':
                    debug_enabled = not debug_enabled
                    # Recreate chatbot with new setting
                    chatbot = SimpleWeatherChatbot(debug_logging=debug_enabled)
                    await chatbot.initialize()
                    print(f"\n🔧 Debug logging: {'ON' if debug_enabled else 'OFF'}")
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


async def demo_mode(show_debug: bool = False):
    """Run a demo showing Strands and MCP in action."""
    chatbot = SimpleWeatherChatbot(debug_logging=show_debug)
    
    if show_debug:
        print("🌤️  AWS Strands Weather Demo with Debug Logging")
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
        '--debug',
        action='store_true',
        help='Show debug logging with tool calls'
    )
    
    parser.add_argument(
        '--multi-turn-demo',
        action='store_true',
        help='Run multi-turn conversation demo'
    )
    
    args = parser.parse_args()
    
    if args.multi_turn_demo:
        try:
            from .demo_scenarios import run_mcp_multi_turn_demo
        except ImportError:
            from demo_scenarios import run_mcp_multi_turn_demo
        await run_mcp_multi_turn_demo(structured=args.debug)
    elif args.demo:
        await demo_mode(show_debug=args.debug)
    else:
        await interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())