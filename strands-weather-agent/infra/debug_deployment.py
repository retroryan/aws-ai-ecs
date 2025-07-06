#!/usr/bin/env python3
"""Debug deployment issues with Langfuse integration"""

import requests
import json
import time

def test_simple_query(url):
    """Test a simple query and show full response"""
    print("\n🔍 Testing simple query...")
    
    response = requests.post(
        f"{url}/query",
        json={"query": "What is 2+2?"},
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
def test_coordinate_issue(url):
    """Test the coordinate formatting issue"""
    print("\n🗺️ Testing coordinate issue...")
    
    # Test with a query that might trigger coordinate usage
    response = requests.post(
        f"{url}/query",
        json={"query": "Weather in Seattle using coordinates 47.6062, -122.3321"},
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response length: {len(data['response'])}")
    
    # Look for the error pattern
    if "apologize" in data['response']:
        print("⚠️ Found formatting error in response")
        print("First 500 chars:", data['response'][:500])
    else:
        print("✅ No formatting error detected")

def test_langfuse_impact(url):
    """Test if Langfuse is causing issues"""
    print("\n📊 Testing multiple queries for Langfuse impact...")
    
    queries = [
        "What's the temperature in Paris?",
        "Is it raining in London?",
        "Weather forecast for Tokyo"
    ]
    
    for i, query in enumerate(queries):
        print(f"\nQuery {i+1}: {query}")
        start = time.time()
        
        try:
            response = requests.post(
                f"{url}/query",
                json={"query": query},
                timeout=30
            )
            elapsed = time.time() - start
            
            print(f"  Status: {response.status_code}")
            print(f"  Time: {elapsed:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Session ID: {data.get('session_id', 'N/A')}")
                if "apologize" in data['response']:
                    print("  ⚠️ Formatting error detected")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")

def main():
    # Get ALB URL
    url = "http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com"
    
    print(f"🎯 Testing deployment at: {url}")
    
    # Run tests
    test_simple_query(url)
    test_coordinate_issue(url)
    test_langfuse_impact(url)
    
    print("\n✅ Debug tests complete")

if __name__ == "__main__":
    main()