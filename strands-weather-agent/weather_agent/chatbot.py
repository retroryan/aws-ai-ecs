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
import os
import logging
from typing import Optional, List
from datetime import datetime
from pathlib import Path

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


def configure_debug_logging(enable_debug: bool = False):
    """
    Configure debug logging for AWS Strands with file output.
    
    Args:
        enable_debug: Whether to enable debug logging
    """
    if not enable_debug:
        return
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"chatbot_debug_{timestamp}.log"
    
    # Configure root logger for debug
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler - INFO level for cleaner output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s | %(name)s | %(message)s")
    console_handler.setFormatter(console_formatter)
    
    # File handler - DEBUG level for detailed logs
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Enable debug for specific Strands modules as per the guide
    logging.getLogger("strands").setLevel(logging.DEBUG)
    logging.getLogger("strands.tools").setLevel(logging.DEBUG)
    logging.getLogger("strands.models").setLevel(logging.DEBUG)
    logging.getLogger("strands.event_loop").setLevel(logging.DEBUG)
    logging.getLogger("strands.agent").setLevel(logging.DEBUG)
    
    # Also enable debug for our modules
    logging.getLogger("weather_agent").setLevel(logging.DEBUG)
    logging.getLogger("__main__").setLevel(logging.DEBUG)
    
    print(f"\n🔍 Debug logging enabled. Logs will be written to: {log_file}")
    print("📊 Console will show INFO level, file will contain DEBUG details.\n")


class SimpleWeatherChatbot:
    """A simple chatbot that uses MCP servers for weather data via Strands."""
    
    def __init__(self, 
                 debug_logging: bool = False,
                 telemetry_user_id: Optional[str] = None,
                 telemetry_session_id: Optional[str] = None,
                 telemetry_tags: Optional[List[str]] = None):
        self.agent: Optional[MCPWeatherAgent] = None
        self.debug_logging = debug_logging
        self.telemetry_user_id = telemetry_user_id
        self.telemetry_session_id = telemetry_session_id
        self.telemetry_tags = telemetry_tags or ["chatbot"]
        self.initialized = False
    
    async def initialize(self):
        """Initialize the Strands agent with MCP connections."""
        if not self.initialized:
            print("🔧 Initializing Weather Agent...")
            
            self.agent = await create_weather_agent(
                debug_logging=self.debug_logging,
                enable_telemetry=None,  # Auto-detect
                telemetry_user_id=self.telemetry_user_id,
                telemetry_session_id=self.telemetry_session_id,
                telemetry_tags=self.telemetry_tags
            )
            
            self.initialized = True
            print("✅ Weather Agent ready!")
    
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
        
        # Show query processing start
        print("\n" + "="*60)
        print("🔄 PROCESSING YOUR QUERY")
        print("="*60)
        print(f"📝 Query: {query}\n")
        
        # Process with Strands agent
        response = await self.agent.query(query)
        
        # Display metrics if available
        if hasattr(self.agent, 'last_metrics') and self.agent.last_metrics:
            try:
                from .metrics_display import format_metrics
            except ImportError:
                from metrics_display import format_metrics
            print(format_metrics(self.agent.last_metrics))
        
        # Show completion
        print("\n" + "="*60)
        print("✅ RESPONSE COMPLETE")
        print("="*60)
        
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
    
    chatbot = SimpleWeatherChatbot(
        telemetry_user_id="interactive-user",
        telemetry_tags=["chatbot", "interactive"]
    )
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
                    chatbot = SimpleWeatherChatbot(
                        debug_logging=debug_enabled,
                        telemetry_user_id="interactive-user",
                        telemetry_tags=["chatbot", "interactive"]
                    )
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
    demo_session_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    chatbot = SimpleWeatherChatbot(
        debug_logging=show_debug,
        telemetry_user_id="demo-user",
        telemetry_session_id=demo_session_id,
        telemetry_tags=["chatbot", "demo", "weather-agent"]
    )
    
    if show_debug:
        print("🌤️  AWS Strands Weather Demo with Debug Logging")
        print("=" * 50)
        print("This demo shows how AWS Strands works with MCP:")
        print("1. Native MCP tool integration")
        print("2. Automatic tool discovery and execution")
        print("3. Clean, simple API design")
        print("4. 50% less code than traditional frameworks")
        print("\n🔍 DEBUG MODE ENABLED:")
        print("   - Model's natural language will appear as it streams")
        print("   - 🔧 [AGENT DEBUG - Tool Call] = Our agent's tool usage logging")
        print("   - 📥 [AGENT DEBUG - Tool Input] = Tool parameters being sent")
        print("   - Strands internal debug logs = Framework's internal processing\n")
    else:
        print("🌤️  AWS Strands Weather Demo")
        print("=" * 50)
        print("This demo shows AWS Strands with MCP servers.")
        print("Experience the simplicity of modern AI agents.\n")
    
    # Initialize session metrics
    try:
        from .metrics_display import SessionMetrics
    except ImportError:
        from metrics_display import SessionMetrics
    
    session_metrics = SessionMetrics()
    
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
            print(f"\n{'#'*70}")
            print(f"# DEMO QUERY {i} OF 3")
            print(f"{'#'*70}")
            
            response = await chatbot.chat(query)
            print(f"\n🤖 Assistant: {response}")
            
            # Add metrics to session if available
            if hasattr(chatbot.agent, 'last_metrics') and chatbot.agent.last_metrics:
                session_metrics.add_query(chatbot.agent.last_metrics)
            
            # Brief pause between queries
            if i < 3:
                print("\n⏸️  Pausing before next query...")
                await asyncio.sleep(2)
        
        print("\n✨ Demo complete! The full system supports many more queries.")
        
        # Show session summary
        print(session_metrics.get_summary())
        
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
        help='Enable debug logging with detailed Strands traces to file'
    )
    
    parser.add_argument(
        '--multi-turn-demo',
        action='store_true',
        help='Run multi-turn conversation demo'
    )
    
    args = parser.parse_args()
    
    # Configure debug logging if requested
    if args.debug:
        configure_debug_logging(enable_debug=True)
    
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