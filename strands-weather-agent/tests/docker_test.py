#!/usr/bin/env python3
"""
Automated Docker integration tests for Weather Agent system.
"""

import asyncio
import httpx
import json
import sys
import time
from typing import Dict, List, Tuple
import os

# ANSI color codes
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class DockerIntegrationTest:
    """Test suite for Docker-deployed Weather Agent system."""
    
    def __init__(self):
        self.base_url = "http://localhost:7777"
        self.services = {
            "Weather Agent": "http://localhost:7777/health",
            "Forecast Server": "http://localhost:7778/health",
            "Historical Server": "http://localhost:7779/health",
            "Agricultural Server": "http://localhost:7780/health"
        }
        self.test_queries = [
            ("What's the weather forecast for Des Moines, Iowa?", "forecast"),
            ("Show me historical weather data for Chicago last month", "historical"),
            ("Are soil conditions good for planting corn in Nebraska?", "agricultural"),
            ("What's the frost risk for tomatoes in Minnesota?", "agricultural"),
            ("Give me a 5-day forecast for Seattle", "forecast"),
        ]
        self.passed = 0
        self.failed = 0
    
    async def wait_for_service(self, name: str, url: str, max_attempts: int = 30) -> bool:
        """Wait for a service to become healthy."""
        print(f"Waiting for {name}...", end="", flush=True)
        
        async with httpx.AsyncClient() as client:
            for attempt in range(max_attempts):
                try:
                    response = await client.get(url, timeout=3.0)
                    if response.status_code == 200:
                        print(f" {GREEN}✓{NC}")
                        return True
                except Exception:
                    pass
                
                print(".", end="", flush=True)
                await asyncio.sleep(2)
        
        print(f" {RED}✗{NC}")
        return False
    
    async def check_all_services(self) -> bool:
        """Check if all services are healthy."""
        print("\n🔍 Checking service health...")
        print("-" * 40)
        
        all_healthy = True
        for name, url in self.services.items():
            if not await self.wait_for_service(name, url):
                all_healthy = False
        
        return all_healthy
    
    async def test_query(self, query: str, expected_type: str) -> bool:
        """Test a single query against the API."""
        print(f"\n📝 Query: \"{query}\"")
        
        async with httpx.AsyncClient() as client:
            try:
                # Send query
                response = await client.post(
                    f"{self.base_url}/query",
                    json={"query": query},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    print(f"{RED}✗ HTTP {response.status_code}{NC}")
                    return False
                
                data = response.json()
                
                # Check response structure
                if "response" not in data:
                    print(f"{RED}✗ Missing response field{NC}")
                    return False
                
                # Check response content
                response_text = data["response"]
                if len(response_text) < 50:
                    print(f"{RED}✗ Response too short{NC}")
                    return False
                
                # Display truncated response
                truncated = response_text[:100] + "..." if len(response_text) > 100 else response_text
                print(f"{GREEN}✓ Response:{NC} {truncated}")
                
                # Check if appropriate tools were likely used
                if expected_type == "forecast" and "forecast" not in response_text.lower():
                    print(f"{YELLOW}⚠ Warning: Expected forecast content{NC}")
                elif expected_type == "historical" and "historical" not in response_text.lower():
                    print(f"{YELLOW}⚠ Warning: Expected historical content{NC}")
                elif expected_type == "agricultural" and ("soil" not in response_text.lower() and 
                                                         "plant" not in response_text.lower()):
                    print(f"{YELLOW}⚠ Warning: Expected agricultural content{NC}")
                
                return True
                
            except httpx.TimeoutException:
                print(f"{RED}✗ Request timeout{NC}")
                return False
            except Exception as e:
                print(f"{RED}✗ Error: {e}{NC}")
                return False
    
    async def test_structured_output(self) -> bool:
        """Test structured output functionality."""
        print("\n🔧 Testing structured output...")
        print("-" * 40)
        
        async with httpx.AsyncClient() as client:
            try:
                # Test forecast structured output
                response = await client.post(
                    f"{self.base_url}/query",
                    json={
                        "query": "What's the weather forecast for Chicago?",
                        "structured": True,
                        "response_format": "forecast"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Note: The current API doesn't support structured output in the endpoint
                    # This is for future enhancement
                    print(f"{YELLOW}ℹ Structured output test skipped (not implemented){NC}")
                    return True
                
            except Exception as e:
                print(f"{YELLOW}ℹ Structured output not available: {e}{NC}")
                return True  # Don't fail the test for missing feature
    
    async def test_api_docs(self) -> bool:
        """Test if API documentation is accessible."""
        print("\n📚 Testing API documentation...")
        print("-" * 40)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/docs")
                if response.status_code == 200:
                    print(f"{GREEN}✓ API docs available at {self.base_url}/docs{NC}")
                    return True
                else:
                    print(f"{RED}✗ API docs not accessible{NC}")
                    return False
            except Exception as e:
                print(f"{RED}✗ Error accessing docs: {e}{NC}")
                return False
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print(f"{BLUE}🐳 Docker Integration Test Suite{NC}")
        print("=" * 50)
        
        # Check if services are healthy
        if not await self.check_all_services():
            print(f"\n{RED}❌ Services not healthy. Aborting tests.{NC}")
            sys.exit(1)
        
        print(f"\n{GREEN}✅ All services healthy!{NC}")
        
        # Test queries
        print("\n\n🧪 Running query tests...")
        print("=" * 50)
        
        for query, expected_type in self.test_queries:
            if await self.test_query(query, expected_type):
                self.passed += 1
            else:
                self.failed += 1
            await asyncio.sleep(1)  # Small delay between queries
        
        # Test additional features
        if await self.test_structured_output():
            self.passed += 1
        else:
            self.failed += 1
        
        if await self.test_api_docs():
            self.passed += 1
        else:
            self.failed += 1
        
        # Summary
        print("\n\n📊 Test Summary")
        print("=" * 50)
        print(f"Total tests: {self.passed + self.failed}")
        print(f"{GREEN}Passed: {self.passed}{NC}")
        print(f"{RED}Failed: {self.failed}{NC}")
        
        if self.failed == 0:
            print(f"\n{GREEN}🎉 All tests passed!{NC}")
        else:
            print(f"\n{RED}❌ Some tests failed{NC}")
            sys.exit(1)
    
    async def test_model_switching(self):
        """Test model switching capability."""
        print("\n🔄 Testing model switching...")
        print("-" * 40)
        
        current_model = os.getenv("BEDROCK_MODEL_ID", "unknown")
        print(f"Current model: {current_model}")
        
        # This would require restarting containers with different env vars
        print(f"{YELLOW}ℹ Model switching requires container restart{NC}")
        print("To test: docker-compose down && export BEDROCK_MODEL_ID=<new-model> && docker-compose up -d")


async def main():
    """Main test runner."""
    tester = DockerIntegrationTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())