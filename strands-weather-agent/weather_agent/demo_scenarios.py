#!/usr/bin/env python3
"""
Multi-turn conversation demo scenarios for AWS Strands Weather Agent

This module demonstrates AWS Strands' multi-turn conversation capabilities,
showing how the agent maintains context across multiple interactions.
"""

import asyncio
from typing import Optional
from .mcp_agent import create_weather_agent, MCPWeatherAgent


async def run_mcp_multi_turn_demo(structured: bool = False):
    """
    Run a multi-turn conversation demo showing how AWS Strands
    maintains context across multiple user interactions.
    
    Args:
        structured: Whether to show detailed tool calls
    """
    print("\n🌤️  AWS Strands Multi-Turn Conversation Demo")
    print("=" * 50)
    print("This demo shows how AWS Strands maintains context")
    print("across multiple turns in a conversation.")
    print("=" * 50)
    
    # Initialize the agent
    print("\n🔌 Initializing AWS Strands agent with MCP connections...")
    agent = await create_weather_agent(structured)
    print("✅ Ready for multi-turn conversation!\n")
    
    # Multi-turn conversation scenarios
    conversation_turns = [
        {
            "turn": 1,
            "query": "What's the weather like in Seattle?",
            "description": "Initial weather query"
        },
        {
            "turn": 2,
            "query": "How does it compare to Portland?",
            "description": "Comparison with context from previous turn"
        },
        {
            "turn": 3,
            "query": "Which city would be better for outdoor activities this weekend?",
            "description": "Decision-making based on accumulated context"
        },
        {
            "turn": 4,
            "query": "What about historical temperatures - has Seattle been warmer than usual?",
            "description": "Adding historical context to the conversation"
        },
        {
            "turn": 5,
            "query": "I'm thinking of planting tomatoes. Based on what you know about Seattle's weather, is it a good time?",
            "description": "Switching to agricultural context while maintaining location"
        }
    ]
    
    try:
        for turn in conversation_turns:
            print(f"\n{'='*50}")
            print(f"Turn {turn['turn']}: {turn['description']}")
            print(f"{'='*50}")
            print(f"👤 User: {turn['query']}")
            
            # Process the query with streaming response
            print(f"🤖 Assistant: ", end="", flush=True)
            
            response = await agent.query(turn['query'])
            
            # Print the response content
            if hasattr(response, 'content'):
                print(response.content)
            else:
                print(response)
            
            # Add a small delay between turns for readability
            await asyncio.sleep(1)
        
        print("\n" + "="*50)
        print("✨ Multi-turn conversation demo complete!")
        print("Notice how the agent maintains context throughout.")
        print("This is AWS Strands' built-in session management.")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Error during multi-turn demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if hasattr(agent, 'cleanup'):
            await agent.cleanup()


async def run_context_switching_demo(structured: bool = False):
    """
    Demonstrate context switching capabilities in multi-turn conversations.
    
    This shows how AWS Strands can handle topic changes while maintaining
    relevant context from previous turns.
    """
    print("\n🔄 AWS Strands Context Switching Demo")
    print("=" * 50)
    print("This demo shows sophisticated context handling")
    print("across topic changes in conversation.")
    print("=" * 50)
    
    # Initialize the agent
    print("\n🔌 Initializing AWS Strands agent...")
    agent = await create_weather_agent(structured)
    print("✅ Ready for context switching demo!\n")
    
    # Context switching scenarios
    scenarios = [
        {
            "turn": 1,
            "query": "Tell me about the weather in Miami and Phoenix",
            "description": "Initial multi-location query"
        },
        {
            "turn": 2,
            "query": "I'm planning to grow citrus fruits. Which location is better?",
            "description": "Switching to agriculture while maintaining locations"
        },
        {
            "turn": 3,
            "query": "What about Denver? How's the weather there?",
            "description": "Adding a new location to the context"
        },
        {
            "turn": 4,
            "query": "Can I grow citrus there too?",
            "description": "Applying previous agricultural context to new location"
        },
        {
            "turn": 5,
            "query": "Give me a summary of all three cities for both weather and agriculture",
            "description": "Comprehensive summary using all accumulated context"
        }
    ]
    
    try:
        for scenario in scenarios:
            print(f"\n{'='*50}")
            print(f"Turn {scenario['turn']}: {scenario['description']}")
            print(f"{'='*50}")
            print(f"👤 User: {scenario['query']}")
            
            # Process the query
            print(f"🤖 Assistant: ", end="", flush=True)
            
            response = await agent.query(scenario['query'])
            
            # Print the response
            if hasattr(response, 'content'):
                print(response.content)
            else:
                print(response)
            
            await asyncio.sleep(1)
        
        print("\n" + "="*50)
        print("✨ Context switching demo complete!")
        print("AWS Strands seamlessly handles topic changes.")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Error during context switching demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(agent, 'cleanup'):
            await agent.cleanup()


async def main():
    """Run all demo scenarios."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-turn conversation demos")
    parser.add_argument('--structured', action='store_true', 
                       help='Show detailed tool calls')
    parser.add_argument('--context-switching', action='store_true',
                       help='Run context switching demo instead')
    
    args = parser.parse_args()
    
    if args.context_switching:
        await run_context_switching_demo(args.structured)
    else:
        await run_mcp_multi_turn_demo(args.structured)


if __name__ == "__main__":
    asyncio.run(main())