#!/usr/bin/env python3
"""Test to isolate the coordinate formatting issue"""

import requests
import json
import time

def test_queries():
    """Test various query formats to isolate the issue"""
    
    base_url = "http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com"
    
    test_cases = [
        # Test 1: Simple city name (should work)
        {
            "name": "Simple city name",
            "query": "What's the weather in Boston?"
        },
        # Test 2: City with known coordinates (triggers error)
        {
            "name": "Seattle (triggers coordinate attempt)",
            "query": "What's the weather in Seattle?"
        },
        # Test 3: Explicit coordinates in query
        {
            "name": "Explicit coordinates",
            "query": "What's the weather at latitude 40.7128 and longitude -74.0060?"
        },
        # Test 4: Mixed format
        {
            "name": "City with coordinates",
            "query": "What's the weather in New York (40.7128, -74.0060)?"
        }
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test {i+1}: {test['name']}")
        print(f"Query: {test['query']}")
        print('='*60)
        
        start = time.time()
        try:
            response = requests.post(
                f"{base_url}/query",
                json={"query": test["query"]},
                timeout=30
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                response_text = data["response"]
                
                # Check for the error pattern
                if "apologize for the formatting error" in response_text:
                    print("❌ FORMATTING ERROR DETECTED")
                    # Extract the part before and after the error
                    parts = response_text.split("apologize for the formatting error")
                    if len(parts) > 0:
                        print(f"Before error: {parts[0][-100:]}...")
                    print("Error message: I apologize for the formatting error...")
                    if len(parts) > 1:
                        print(f"After error: ...{parts[1][:100]}")
                else:
                    print("✅ No formatting error")
                    print(f"Response preview: {response_text[:200]}...")
                
                print(f"\nSession ID: {data.get('session_id', 'N/A')}")
                print(f"Response time: {elapsed:.2f}s")
            else:
                print(f"❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*60)
    print("ANALYSIS:")
    print("- The error occurs when the agent tries to use location coordinates")
    print("- The agent appears to attempt using coordinates first, fails, then retries with location name")
    print("- This suggests an issue with how coordinates are being formatted in tool calls")

if __name__ == "__main__":
    print("🔍 Testing Coordinate Formatting Issue")
    test_queries()