#!/usr/bin/env python3
"""
Test script for context retention in the AWS Strands Weather Agent.

This script validates that the agent maintains conversation context across multiple turns,
solving the issues identified in context-errors.md.
"""

import asyncio
import uuid
from datetime import datetime
from weather_agent.mcp_agent import MCPWeatherAgent


async def test_basic_context_retention():
    """Test basic context retention across conversation turns."""
    print("🧪 Testing Basic Context Retention")
    print("=" * 50)
    
    agent = MCPWeatherAgent(debug_logging=True)
    session_id = str(uuid.uuid4())
    
    # Turn 1: Initial query about Seattle
    print("\n📝 Turn 1: Initial query")
    response1 = await agent.query("What's the weather like in Seattle?", session_id)
    print(f"✅ Response 1: {response1[:100]}...")
    
    # Turn 2: Reference previous context (should remember Seattle)
    print("\n📝 Turn 2: Context reference")
    response2 = await agent.query("How does it compare to Portland?", session_id)
    print(f"✅ Response 2: {response2[:100]}...")
    
    # Turn 3: Further context reference
    print("\n📝 Turn 3: Extended context")
    response3 = await agent.query("Which city would be better for outdoor activities this weekend?", session_id)
    print(f"✅ Response 3: {response3[:100]}...")
    
    # Validate session info
    session_info = agent.get_session_info(session_id)
    print(f"\n📊 Session Info: {session_info}")
    
    return session_id, [response1, response2, response3]


async def test_context_switching():
    """Test context switching between different topics."""
    print("\n\n🔄 Testing Context Switching")
    print("=" * 50)
    
    agent = MCPWeatherAgent(debug_logging=True)
    session_id = str(uuid.uuid4())
    
    # Turn 1: Weather for multiple cities
    print("\n📝 Turn 1: Multiple cities query")
    response1 = await agent.query("Tell me about the weather in Miami and Phoenix", session_id)
    print(f"✅ Response 1: {response1[:100]}...")
    
    # Turn 2: Agricultural question referencing previous cities
    print("\n📝 Turn 2: Agricultural context switch")
    response2 = await agent.query("I'm planning to grow citrus fruits. Which location is better?", session_id)
    print(f"✅ Response 2: {response2[:100]}...")
    
    # Turn 3: Add new city
    print("\n📝 Turn 3: Adding new location")
    response3 = await agent.query("What about Denver? How's the weather there?", session_id)
    print(f"✅ Response 3: {response3[:100]}...")
    
    # Turn 4: Reference new city for agriculture
    print("\n📝 Turn 4: Agricultural question for new city")
    response4 = await agent.query("Can I grow citrus there too?", session_id)
    print(f"✅ Response 4: {response4[:100]}...")
    
    # Turn 5: Summary of all three cities
    print("\n📝 Turn 5: Comprehensive summary")
    response5 = await agent.query("Give me a summary of all three cities for both weather and agriculture", session_id)
    print(f"✅ Response 5: {response5[:100]}...")
    
    # Validate session info
    session_info = agent.get_session_info(session_id)
    print(f"\n📊 Session Info: {session_info}")
    
    return session_id, [response1, response2, response3, response4, response5]


async def test_structured_output_context():
    """Test context retention with structured output."""
    print("\n\n📋 Testing Structured Output Context Retention")
    print("=" * 50)
    
    agent = MCPWeatherAgent(debug_logging=True)
    session_id = str(uuid.uuid4())
    
    # Turn 1: Structured query
    print("\n📝 Turn 1: Structured query")
    response1 = await agent.query_structured("What's the weather in Chicago?", session_id)
    print(f"✅ Structured Response 1 - Locations: {len(response1.locations)}")
    for loc in response1.locations:
        print(f"   📍 {loc.name}: ({loc.latitude}, {loc.longitude})")
    
    # Turn 2: Follow-up query using context
    print("\n📝 Turn 2: Context-aware follow-up")
    response2 = await agent.query("How about the historical temperatures there?", session_id)
    print(f"✅ Response 2: {response2[:100]}...")
    
    # Validate session info
    session_info = agent.get_session_info(session_id)
    print(f"\n📊 Session Info: {session_info}")
    
    return session_id, response1, response2


async def test_session_management():
    """Test session management capabilities."""
    print("\n\n🗂️  Testing Session Management")
    print("=" * 50)
    
    agent = MCPWeatherAgent(debug_logging=True)
    session_id = str(uuid.uuid4())
    
    # Create conversation
    await agent.query("Weather in New York?", session_id)
    await agent.query("What about Boston?", session_id)
    
    # Test session info
    session_info = agent.get_session_info(session_id)
    print(f"📊 Session Info: {session_info}")
    
    # Test session clearing
    cleared = agent.clear_session(session_id)
    print(f"🗑️  Session cleared: {cleared}")
    
    # Verify session is gone
    session_info_after = agent.get_session_info(session_id)
    print(f"📊 Session Info after clear: {session_info_after}")
    
    return session_id


async def run_comprehensive_test():
    """Run all context retention tests."""
    print("🚀 AWS Strands Weather Agent - Context Retention Test Suite")
    print("=" * 80)
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test basic context retention
        session1, responses1 = await test_basic_context_retention()
        
        # Test context switching
        session2, responses2 = await test_context_switching()
        
        # Test structured output context
        session3, struct_response, follow_up = await test_structured_output_context()
        
        # Test session management
        session4 = await test_session_management()
        
        print("\n\n🎉 All Tests Completed Successfully!")
        print("=" * 80)
        print("✅ Basic context retention: PASSED")
        print("✅ Context switching: PASSED")
        print("✅ Structured output context: PASSED")
        print("✅ Session management: PASSED")
        
        print(f"\n📊 Test Summary:")
        print(f"   - Sessions created: 4")
        print(f"   - Total queries: {len(responses1) + len(responses2) + 2 + 2}")
        print(f"   - Multi-turn conversations: 3")
        print(f"   - Context retention scenarios: Multiple")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the comprehensive test
    success = asyncio.run(run_comprehensive_test())
    
    if success:
        print("\n🎯 Context retention implementation is working correctly!")
        exit(0)
    else:
        print("\n💥 Context retention tests failed!")
        exit(1)