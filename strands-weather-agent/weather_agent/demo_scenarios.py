#!/usr/bin/env python3
"""
Multi-turn conversation demo scenarios for AWS Strands Weather Agent

This module demonstrates AWS Strands' multi-turn conversation capabilities,
showing how the agent maintains context across multiple interactions using
session-based conversation management.
"""

import asyncio
import uuid
from typing import Optional

# Handle both module and direct script execution
try:
    from .mcp_agent import create_weather_agent, MCPWeatherAgent
    from .metrics_display import SessionMetrics
except ImportError:
    from mcp_agent import create_weather_agent, MCPWeatherAgent
    from metrics_display import SessionMetrics


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
    print("across multiple turns in a conversation using")
    print("session-based conversation management.")
    print("=" * 50)
    
    if structured:
        print("\n🔍 DEBUG MODE ENABLED:")
        print("   - Model's natural language will appear as it streams")
        print("   - 🔧 [AGENT DEBUG - Tool Call] = Our agent's tool usage logging")
        print("   - 📥 [AGENT DEBUG - Tool Input] = Tool parameters being sent")
        print("   - Strands internal debug logs = Framework's internal processing")
    
    # Initialize the agent
    print("\n🔌 Initializing AWS Strands agent with MCP connections...")
    agent = await create_weather_agent(structured)
    
    # Create a session ID for this conversation
    session_id = str(uuid.uuid4())
    print(f"✅ Ready for multi-turn conversation!")
    print(f"🆔 Session ID: {session_id[:8]}...\n")
    
    # Initialize session metrics
    session_metrics = SessionMetrics()
    
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
            print(f"\n{'#'*70}")
            print(f"# CONVERSATION TURN {turn['turn']}: {turn['description']}")
            print(f"{'#'*70}")
            print(f"👤 User: {turn['query']}")
            
            # Show query processing start
            print("\n" + "="*60)
            print("🔄 PROCESSING YOUR QUERY")
            print("="*60)
            print(f"📝 Query: {turn['query']}\n")
            
            # Process the query with session context
            response_obj = await agent.query(turn['query'], session_id=session_id)
            response = response_obj.summary
            
            # Display metrics if available
            if hasattr(agent, 'last_metrics') and agent.last_metrics:
                try:
                    from .metrics_display import format_metrics
                except ImportError:
                    from metrics_display import format_metrics
                print(format_metrics(agent.last_metrics))
                # Add to session metrics
                session_metrics.add_query(agent.last_metrics)
            
            # Show completion
            print("\n" + "="*60)
            print("✅ RESPONSE COMPLETE")
            print("="*60)
            
            # Print the response
            print(f"\n🤖 Assistant: ", end="")
            if hasattr(response, 'content'):
                print(response.content)
            else:
                print(response)
            
            # Add a small delay between turns for readability
            await asyncio.sleep(1)
        
        print("\n" + "="*50)
        print("✨ Multi-turn conversation demo complete!")
        print("Notice how the agent maintains context throughout.")
        print("This is AWS Strands' session-based context retention.")
        
        # Show session information
        session_info = agent.get_session_info(session_id)
        if session_info:
            print(f"\n📊 Session Statistics:")
            print(f"   🔢 Total messages: {session_info['total_messages']}")
            print(f"   🔄 Conversation turns: {session_info['conversation_turns']}")
            print(f"   💾 Storage type: {session_info['storage_type']}")
        
        # Show session metrics summary
        print(session_metrics.get_summary())
        
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
    print("across topic changes in conversation using")
    print("session-based conversation management.")
    print("=" * 50)
    
    # Initialize the agent
    print("\n🔌 Initializing AWS Strands agent...")
    agent = await create_weather_agent(structured)
    
    # Create a session ID for this conversation
    session_id = str(uuid.uuid4())
    print(f"✅ Ready for context switching demo!")
    print(f"🆔 Session ID: {session_id[:8]}...\n")
    
    # Initialize session metrics
    session_metrics = SessionMetrics()
    
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
            
            # Process the query with session context
            print(f"🤖 Assistant: ", end="", flush=True)
            
            response_obj = await agent.query(scenario['query'], session_id=session_id)
            response = response_obj.summary
            
            # Print the response
            if hasattr(response, 'content'):
                print(response.content)
            else:
                print(response)
            
            # Display metrics if available
            if hasattr(agent, 'last_metrics') and agent.last_metrics:
                try:
                    from .metrics_display import format_metrics
                except ImportError:
                    from metrics_display import format_metrics
                print(format_metrics(agent.last_metrics))
                # Add to session metrics
                session_metrics.add_query(agent.last_metrics)
            
            await asyncio.sleep(1)
        
        print("\n" + "="*50)
        print("✨ Context switching demo complete!")
        print("AWS Strands seamlessly handles topic changes")
        print("with session-based context retention.")
        
        # Show session information
        session_info = agent.get_session_info(session_id)
        if session_info:
            print(f"\n📊 Session Statistics:")
            print(f"   🔢 Total messages: {session_info['total_messages']}")
            print(f"   🔄 Conversation turns: {session_info['conversation_turns']}")
            print(f"   💾 Storage type: {session_info['storage_type']}")
        
        # Show session metrics summary
        print(session_metrics.get_summary())
        
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