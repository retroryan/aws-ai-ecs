#!/usr/bin/env python3
"""
MCP Weather Chatbot with Structured Output Support

This demonstrates how MCP servers work over streaming HTTP and how
structured output works with LangGraph:
- Shows tool calls and their raw JSON responses
- Demonstrates the transformation from raw data to structured output
- Logs the structured output models for transparency
- Supports multi-turn conversations with context retention

Usage:
    python chatbot.py                     # Interactive mode
    python chatbot.py --demo              # Demo mode with example queries
    python chatbot.py --multi-turn-demo   # Multi-turn conversation demo
    python chatbot.py --structured        # Enable structured output display
"""

import sys
import json
from typing import Optional

# Handle imports whether run from project root or weather_agent directory
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if os.path.basename(os.getcwd()) == 'weather_agent':
    # Running from weather_agent directory
    sys.path.insert(0, parent_dir)
else:
    # Running from project root
    sys.path.insert(0, current_dir)

from weather_agent.mcp_agent import MCPWeatherAgent
from weather_agent.models import OpenMeteoResponse, AgricultureAssessment


class SimpleWeatherChatbot:
    """A simple chatbot that uses MCP servers for weather data."""
    
    def __init__(self):
        self.agent = MCPWeatherAgent()
        self.initialized = False
    
    def initialize(self):
        """Initialize MCP connections."""
        if not self.initialized:
            print("🔌 Initializing MCP connections...")
            self.agent.initialize()
            self.initialized = True
            print("✅ Ready to answer weather questions!\n")
    
    def log_tool_calls(self, messages):
        """Extract and log tool calls from agent messages."""
        tool_calls_found = []
        
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for call in msg.tool_calls:
                    tool_calls_found.append({
                        'name': call['name'],
                        'args': call.get('args', {})
                    })
        
        if tool_calls_found:
            print("\n📞 Tool Calls Made:")
            for i, call in enumerate(tool_calls_found, 1):
                print(f"\n{i}. {call['name']}")
                if call['args']:
                    args_json = json.dumps(call['args'], indent=2)
                    print(f"   Arguments: {args_json}")
    
    def log_tool_responses(self, messages):
        """Extract and log tool responses showing raw JSON data."""
        tool_responses = []
        
        for msg in messages:
            # Check if it's specifically a ToolMessage (has type 'tool')
            if hasattr(msg, 'type') and msg.type == 'tool' and hasattr(msg, 'name') and hasattr(msg, 'content'):
                # This is a tool response message
                # Extract the JSON part from the content
                content_str = str(msg.content)
                json_start = content_str.find('{')
                
                if json_start != -1:
                    try:
                        # Extract and parse the JSON portion
                        json_str = content_str[json_start:]
                        # Find the matching closing brace
                        brace_count = 0
                        json_end = -1
                        for i, char in enumerate(json_str):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > 0:
                            json_data = json.loads(json_str[:json_end])
                            tool_responses.append({
                                'tool': msg.name,
                                'content': json_data,
                                'full_content': content_str[:json_start]  # The text before JSON
                            })
                    except:
                        # If JSON parsing fails, store the raw content
                        tool_responses.append({
                            'tool': msg.name,
                            'content': content_str
                        })
                else:
                    # No JSON found, store as is
                    tool_responses.append({
                        'tool': msg.name,
                        'content': content_str
                    })
        
        if tool_responses:
            print("\n📊 Raw Tool Responses:")
            for resp in tool_responses:
                print(f"\n{resp['tool']} returned:")
                if 'full_content' in resp:
                    print(resp['full_content'].strip())
                if isinstance(resp['content'], dict):
                    # Truncate to 200 characters as requested
                    preview = json.dumps(resp['content'], indent=2)
                    if len(preview) > 200:
                        preview = preview[:200] + "\n... (truncated)"
                    print(preview)
                elif isinstance(resp['content'], str):
                    # For non-JSON content, also truncate
                    preview = resp['content']
                    if len(preview) > 200:
                        preview = preview[:200] + "... (truncated)"
                    print(preview)
    
    def log_structured_output(self, structured_data):
        """Log the final structured output model."""
        print("\n🏗️  Structured Output Generated:")
        print(f"Type: {type(structured_data).__name__}")
        
        if isinstance(structured_data, OpenMeteoResponse):
            print(f"Location: {structured_data.location}")
            if structured_data.coordinates:
                print(f"Coordinates: {structured_data.coordinates}")
            if structured_data.timezone:
                print(f"Timezone: {structured_data.timezone}")
            if structured_data.current_conditions:
                cc = structured_data.current_conditions
                print(f"Current Temperature: {cc.temperature}°C" if cc.temperature else "Current Temperature: N/A")
                print(f"Current Conditions: {cc.conditions or 'N/A'}")
            if structured_data.daily_forecast:
                print(f"Forecast Days: {len(structured_data.daily_forecast)}")
            
        elif isinstance(structured_data, AgricultureAssessment):
            print(f"Location: {structured_data.location}")
            if structured_data.soil_temperature:
                print(f"Soil Temperature: {structured_data.soil_temperature}°C")
            if structured_data.soil_moisture:
                print(f"Soil Moisture: {structured_data.soil_moisture}")
            print(f"Planting Conditions: {structured_data.planting_conditions}")
            
            if structured_data.recommendations:
                print("Recommendations:")
                for rec in structured_data.recommendations:
                    print(f"  • {rec}")
        
        # Show summary of the full model
        print("\n📄 Full Structured Data (Summary):")
        json_data = structured_data.model_dump()
        # Show key fields only
        summary_fields = ['location', 'summary', 'data_source', 'planting_conditions']
        for field in summary_fields:
            if field in json_data and json_data[field]:
                print(f"  {field}: {json_data[field][:100] if isinstance(json_data[field], str) else json_data[field]}")
    
    def chat(self, query: str, show_structured: bool = False) -> str:
        """Process a user query with optional structured output display."""
        if not self.initialized:
            self.initialize()
        
        try:
            if show_structured:
                # Determine format based on query content
                response_format = "agriculture" if any(
                    word in query.lower() 
                    for word in ['plant', 'soil', 'crop', 'farm', 'grow']
                ) else "forecast"
                
                print(f"\n💭 Processing query for {response_format} format...")
                
                # Get structured response
                structured_response = self.agent.query_structured(query, response_format=response_format)
                
                # Get the conversation history from the checkpoint to log tool calls
                thread_id = self.agent.conversation_id
                config = {"configurable": {"thread_id": thread_id}}
                checkpoint = self.agent.checkpointer.get(config)
                
                if checkpoint and checkpoint.get("channel_values", {}).get("messages"):
                    messages = checkpoint["channel_values"]["messages"]
                    # Log the process
                    self.log_tool_calls(messages)
                    self.log_tool_responses(messages)
                
                self.log_structured_output(structured_response)
                
                # Return the summary
                return structured_response.summary
            else:
                # Regular text response
                response = self.agent.query(query)
                return response
                
        except TimeoutError:
            return "Sorry, the request timed out. Please try again."
        except Exception as e:
            return f"An error occurred: {str(e)}"
    
    def cleanup(self):
        """Clean up MCP connections."""
        if self.initialized:
            self.agent.cleanup()


def interactive_mode(show_structured: bool = False):
    """Run the chatbot in interactive mode."""
    chatbot = SimpleWeatherChatbot()
    
    # Predefined agricultural locations for examples
    AGRICULTURAL_LOCATIONS = {
        "Grand Island, Nebraska": {
            "coordinates": (40.9264, -98.3420),
            "crops": "corn/soybeans",
            "state": "Nebraska"
        },
        "Scottsbluff, Nebraska": {
            "coordinates": (41.8666, -103.6672),
            "crops": "sugar beets/corn",
            "state": "Nebraska"
        },
        "Ames, Iowa": {
            "coordinates": (42.0347, -93.6200),
            "crops": "corn/soybeans",
            "state": "Iowa"
        },
        "Cedar Rapids, Iowa": {
            "coordinates": (41.9779, -91.6656),
            "crops": "corn/soybeans",
            "state": "Iowa"
        },
        "Fresno, California": {
            "coordinates": (36.7468, -119.7726),
            "crops": "grapes/almonds",
            "state": "California"
        },
        "Salinas, California": {
            "coordinates": (36.6777, -121.6555),
            "crops": "lettuce/strawberries",
            "state": "California"
        },
        "Lubbock, Texas": {
            "coordinates": (33.5779, -101.8552),
            "crops": "cotton/sorghum",
            "state": "Texas"
        },
        "Amarillo, Texas": {
            "coordinates": (35.2220, -101.8313),
            "crops": "wheat/cattle",
            "state": "Texas"
        }
    }
    
    print("🌤️  MCP Weather Chatbot")
    print("=" * 50)
    print("Ask me about weather forecasts, historical data,")
    print("or agricultural conditions!")
    print("Type 'exit' or 'quit' to end the session.")
    print("Type 'structured' to toggle structured output display.\n")
    
    print("📍 Example Agricultural Locations:")
    for location, info in AGRICULTURAL_LOCATIONS.items():
        city_state = f"{location.split(',')[0]}, {info['state']}"
        print(f"   • {city_state} - {info['crops']}")
    print()
    
    # Start with structured output setting from command line
    structured_enabled = show_structured
    
    try:
        chatbot.initialize()
        
        if structured_enabled:
            print("\n🔧 Structured output display is ON by default")
            print("   (showing tool calls, raw responses, and structured data)")
        
        while True:
            try:
                query = input("\n🤔 You: ").strip()
                
                if query.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                if query.lower() == 'structured':
                    structured_enabled = not structured_enabled
                    print(f"\n🔧 Structured output display: {'ON' if structured_enabled else 'OFF'}")
                    if structured_enabled:
                        print("   (showing tool calls, raw responses, and structured data)")
                    continue
                
                if not query:
                    continue
                
                print("\n💭 Thinking...")
                response = chatbot.chat(query, show_structured=structured_enabled)
                print(f"\n🤖 Assistant: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
                
    finally:
        chatbot.cleanup()


def demo_mode(show_structured: bool = False):
    """Run a demo showing MCP and structured output in action."""
    chatbot = SimpleWeatherChatbot()
    
    if show_structured:
        print("🌤️  MCP Weather Demo with Structured Output")
        print("=" * 50)
        print("This demo shows how LangGraph Option 1 structured output works:")
        print("1. Tools are called with specific arguments")
        print("2. Raw JSON responses are returned from MCP servers")
        print("3. The agent transforms this into structured Pydantic models")
        print("4. Applications can use either text or structured data\n")
    else:
        print("🌤️  MCP Weather Demo")
        print("=" * 50)
        print("This demo shows MCP servers in action.")
        print("Connecting to MCP servers over streaming HTTP.\n")
    
    try:
        chatbot.initialize()
        
        # Demo queries
        if show_structured:
            # All queries show structured output
            queries = [
                ("What's the weather forecast for Ames, Iowa?", True),
                ("Are conditions good for planting corn in Grand Island, Nebraska?", True)
            ]
        else:
            # Regular demo without structured output
            queries = [
                ("What's the weather forecast for Ames, Iowa?", False),
                ("Show me historical weather for Fresno last month", False),
                ("Are conditions good for planting in Grand Island?", False)
            ]
        
        for i, (query, show_structured) in enumerate(queries, 1):
            print(f"\n{'='*50}")
            print(f"Query {i}: {query}")
            if show_structured:
                print("🏗️  [Structured Output Enabled]")
            print("-" * 50)
            
            response = chatbot.chat(query, show_structured=show_structured)
            print(f"\nResponse: {response}")
            
            if i < len(queries):
                import time
                time.sleep(1)  # Brief pause between queries
        
        print(f"\n{'='*50}")
        print("✅ Demo complete!")
        
        if show_structured:
            print("\nKey Takeaways:")
            print("• Tool calls show how the agent requests specific data")
            print("• Raw JSON responses contain all Open-Meteo data")
            print("• Structured output models provide type-safe access")
            print("• Both text and structured formats are available")
        
    finally:
        chatbot.cleanup()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Weather Chatbot with Structured Output")
    parser.add_argument("--demo", action="store_true", help="Run demo mode")
    parser.add_argument("--multi-turn-demo", action="store_true", dest="multi_turn_demo", help="Run multi-turn conversation demo")
    parser.add_argument("--structured", action="store_true", help="Enable structured output display")
    parser.add_argument("query", nargs="?", help="Single query to process")
    
    args = parser.parse_args()
    
    if args.multi_turn_demo:
        from weather_agent.demo_scenarios import run_mcp_multi_turn_demo
        # Convert async demo to sync
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_mcp_multi_turn_demo(structured=args.structured))
        loop.close()
    elif args.demo:
        demo_mode(show_structured=args.structured)
    elif args.query:
        # Single query mode
        chatbot = SimpleWeatherChatbot()
        try:
            chatbot.initialize()
            response = chatbot.chat(args.query, show_structured=args.structured)
            print(f"\n🤖 Assistant: {response}")
        finally:
            chatbot.cleanup()
    else:
        interactive_mode(show_structured=args.structured)


if __name__ == "__main__":
    main()