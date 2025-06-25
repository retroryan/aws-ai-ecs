#!/usr/bin/env python3
"""
Test different AWS Bedrock models with the weather agent.
This script tests various Bedrock models to ensure they work correctly with tool calling.
"""

import asyncio
import os
import sys
import logging
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weather_agent.mcp_agent import MCPWeatherAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configurations for different Bedrock models
BEDROCK_MODELS = [
    {
        "id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "name": "Claude 3.5 Sonnet",
        "provider": "anthropic"
    },
    {
        "id": "us.anthropic.claude-3-haiku-20240307-v1:0",
        "name": "Claude 3 Haiku",
        "provider": "anthropic"
    },
    {
        "id": "us.meta.llama3-2-11b-instruct-v1:0",
        "name": "Llama 3.2 11B",
        "provider": "meta"
    },
    {
        "id": "us.meta.llama3-1-8b-instruct-v1:0",
        "name": "Llama 3.1 8B",
        "provider": "meta"
    },
    {
        "id": "amazon.nova-micro-v1:0",
        "name": "Amazon Nova Micro",
        "provider": "amazon"
    },
    {
        "id": "amazon.nova-lite-v1:0",
        "name": "Amazon Nova Lite",
        "provider": "amazon"
    }
]

# Test queries to evaluate model performance
TEST_QUERIES = [
    "What's the current weather in Seattle?",
    "Give me a 5-day forecast for Chicago",
    "What were the temperatures in New York last week?",
    "Are conditions good for planting corn in Iowa?",
    "Compare the weather between Miami and Boston"
]

async def test_bedrock_model(model_config: Dict[str, str], use_mock: bool = True) -> Dict[str, Any]:
    """Test a specific Bedrock model."""
    model_id = model_config["id"]
    model_name = model_config["name"]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {model_name} ({model_id})")
    logger.info(f"{'='*60}")
    
    # Set environment variables
    os.environ["MODEL_PROVIDER"] = "bedrock"
    os.environ["BEDROCK_MODEL_ID"] = model_id
    
    results = {
        "model": model_config,
        "queries": [],
        "success_rate": 0,
        "avg_response_time": 0,
        "errors": []
    }
    
    try:
        # Create agent
        agent = MCPWeatherAgent(mock_mode=use_mock)
        logger.info(f"✅ Agent created with model: {model_id}")
        
        # Test connectivity
        connectivity = await agent.test_connectivity()
        logger.info(f"🔗 Connectivity: {connectivity}")
        
        # Test each query
        import time
        total_time = 0
        successful = 0
        
        for query in TEST_QUERIES:
            logger.info(f"\n📝 Query: {query}")
            start_time = time.time()
            
            try:
                response = await agent.query(query)
                elapsed = time.time() - start_time
                total_time += elapsed
                successful += 1
                
                logger.info(f"✅ Response received in {elapsed:.2f}s")
                logger.info(f"📏 Response length: {len(response)} chars")
                
                results["queries"].append({
                    "query": query,
                    "success": True,
                    "response_time": elapsed,
                    "response_length": len(response)
                })
                
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"❌ Error: {str(e)}")
                results["queries"].append({
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "response_time": elapsed
                })
                results["errors"].append(str(e))
        
        # Calculate metrics
        results["success_rate"] = (successful / len(TEST_QUERIES)) * 100
        if successful > 0:
            results["avg_response_time"] = total_time / successful
        
        logger.info(f"\n📊 Results for {model_name}:")
        logger.info(f"   Success Rate: {results['success_rate']:.1f}%")
        logger.info(f"   Avg Response Time: {results['avg_response_time']:.2f}s")
        
    except Exception as e:
        logger.error(f"❌ Failed to create agent: {str(e)}")
        results["errors"].append(f"Agent creation failed: {str(e)}")
    
    return results

async def main():
    """Test all Bedrock models."""
    logger.info("🚀 Starting Bedrock Models Testing")
    logger.info(f"📍 Testing {len(BEDROCK_MODELS)} models with {len(TEST_QUERIES)} queries each")
    
    # Check if we should use mock mode
    use_mock = "--no-mock" not in sys.argv
    if use_mock:
        logger.info("🎭 Using mock mode (no MCP servers required)")
    else:
        logger.info("🔧 Using real MCP servers")
    
    all_results = []
    
    for model_config in BEDROCK_MODELS:
        try:
            results = await test_bedrock_model(model_config, use_mock)
            all_results.append(results)
        except Exception as e:
            logger.error(f"Failed to test {model_config['name']}: {str(e)}")
    
    # Summary report
    logger.info("\n" + "="*60)
    logger.info("📊 SUMMARY REPORT")
    logger.info("="*60)
    
    for result in all_results:
        model_name = result["model"]["name"]
        success_rate = result["success_rate"]
        avg_time = result["avg_response_time"]
        errors = len(result["errors"])
        
        logger.info(f"\n{model_name}:")
        logger.info(f"  ✅ Success Rate: {success_rate:.1f}%")
        logger.info(f"  ⏱️  Avg Response Time: {avg_time:.2f}s")
        logger.info(f"  ❌ Errors: {errors}")
    
    # Find best performing model
    if all_results:
        best_model = max(all_results, key=lambda x: x["success_rate"])
        logger.info(f"\n🏆 Best Model: {best_model['model']['name']} ({best_model['success_rate']:.1f}% success)")

if __name__ == "__main__":
    asyncio.run(main())