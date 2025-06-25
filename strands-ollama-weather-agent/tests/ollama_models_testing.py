#!/usr/bin/env python3
"""
Test different Ollama models with the weather agent.
This script tests various Ollama models to evaluate their tool calling capabilities.
"""

import asyncio
import os
import sys
import logging
import httpx
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

# Test configurations for different Ollama models
# Based on recommendations from STRANDS_OLLAMA_GUIDE.md
OLLAMA_MODELS = [
    {
        "id": "llama3.2",
        "name": "Llama 3.2 (3B)",
        "size": "3B",
        "expected_tool_calling": False,  # Known to struggle with tool calling
        "note": "Fast but poor tool calling"
    },
    {
        "id": "llama3.1:8b",
        "name": "Llama 3.1 (8B)",
        "size": "8B",
        "expected_tool_calling": True,
        "note": "Good tool calling support"
    },
    {
        "id": "mistral:7b",
        "name": "Mistral (7B)",
        "size": "7B",
        "expected_tool_calling": True,
        "note": "Excellent performance"
    },
    {
        "id": "gemma2:9b",
        "name": "Gemma 2 (9B)",
        "size": "9B",
        "expected_tool_calling": True,
        "note": "Strong reasoning"
    },
    {
        "id": "qwen2.5:7b",
        "name": "Qwen 2.5 (7B)",
        "size": "7B",
        "expected_tool_calling": True,
        "note": "Reliable tool usage"
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

async def check_ollama_model_available(model_id: str) -> bool:
    """Check if an Ollama model is available locally."""
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_host}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                return model_id in model_names
    except Exception as e:
        logger.error(f"Failed to check Ollama models: {e}")
    return False

async def test_ollama_model(model_config: Dict[str, Any], use_mock: bool = True) -> Dict[str, Any]:
    """Test a specific Ollama model."""
    model_id = model_config["id"]
    model_name = model_config["name"]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {model_name} ({model_id})")
    logger.info(f"Model Size: {model_config['size']}")
    logger.info(f"Note: {model_config['note']}")
    logger.info(f"{'='*60}")
    
    # Set environment variables
    os.environ["MODEL_PROVIDER"] = "ollama"
    os.environ["OLLAMA_MODEL"] = model_id
    
    results = {
        "model": model_config,
        "available": False,
        "queries": [],
        "success_rate": 0,
        "avg_response_time": 0,
        "tool_calling_success": False,
        "errors": []
    }
    
    # Check if model is available
    model_available = await check_ollama_model_available(model_id)
    results["available"] = model_available
    
    if not model_available:
        logger.warning(f"⚠️  Model {model_id} not available. Run: ollama pull {model_id}")
        results["errors"].append(f"Model not available. Run: ollama pull {model_id}")
        return results
    
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
        tool_calls_detected = 0
        
        for query in TEST_QUERIES:
            logger.info(f"\n📝 Query: {query}")
            start_time = time.time()
            
            try:
                response = await agent.query(query)
                elapsed = time.time() - start_time
                total_time += elapsed
                successful += 1
                
                # Check if response indicates tool usage (heuristic)
                tool_indicators = ["forecast", "temperature", "weather", "conditions", "°", "humidity"]
                has_tool_data = any(indicator in response.lower() for indicator in tool_indicators)
                
                if has_tool_data:
                    tool_calls_detected += 1
                
                logger.info(f"✅ Response received in {elapsed:.2f}s")
                logger.info(f"📏 Response length: {len(response)} chars")
                logger.info(f"🔧 Tool data detected: {has_tool_data}")
                
                # Log first 200 chars of response for debugging
                preview = response[:200] + "..." if len(response) > 200 else response
                logger.debug(f"Response preview: {preview}")
                
                results["queries"].append({
                    "query": query,
                    "success": True,
                    "response_time": elapsed,
                    "response_length": len(response),
                    "tool_data_detected": has_tool_data
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
            results["tool_calling_success"] = tool_calls_detected >= (successful * 0.8)  # 80% threshold
        
        logger.info(f"\n📊 Results for {model_name}:")
        logger.info(f"   Success Rate: {results['success_rate']:.1f}%")
        logger.info(f"   Avg Response Time: {results['avg_response_time']:.2f}s")
        logger.info(f"   Tool Calling Success: {'✅' if results['tool_calling_success'] else '❌'}")
        logger.info(f"   Tool Data Detected: {tool_calls_detected}/{successful} queries")
        
    except Exception as e:
        logger.error(f"❌ Failed to create agent: {str(e)}")
        results["errors"].append(f"Agent creation failed: {str(e)}")
    
    return results

async def main():
    """Test all Ollama models."""
    logger.info("🚀 Starting Ollama Models Testing")
    logger.info(f"📍 Testing {len(OLLAMA_MODELS)} models with {len(TEST_QUERIES)} queries each")
    
    # Check Ollama connectivity
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    logger.info(f"🔗 Ollama host: {ollama_host}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_host}/api/tags", timeout=5.0)
            if response.status_code == 200:
                logger.info("✅ Ollama is running")
            else:
                logger.error("❌ Ollama is not responding properly")
                return
    except Exception as e:
        logger.error(f"❌ Cannot connect to Ollama: {e}")
        logger.info("💡 Make sure Ollama is running: ollama serve")
        return
    
    # Check if we should use mock mode
    use_mock = "--no-mock" not in sys.argv
    if use_mock:
        logger.info("🎭 Using mock mode (no MCP servers required)")
    else:
        logger.info("🔧 Using real MCP servers")
    
    # Test specific models if provided
    test_models = sys.argv[1:] if len(sys.argv) > 1 and sys.argv[1] != "--no-mock" else None
    
    if test_models:
        # Filter to only test specified models
        models_to_test = [m for m in OLLAMA_MODELS if m["id"] in test_models]
        if not models_to_test:
            logger.error(f"❌ No matching models found for: {test_models}")
            logger.info(f"Available models: {[m['id'] for m in OLLAMA_MODELS]}")
            return
    else:
        models_to_test = OLLAMA_MODELS
    
    all_results = []
    
    for model_config in models_to_test:
        try:
            results = await test_ollama_model(model_config, use_mock)
            all_results.append(results)
        except Exception as e:
            logger.error(f"Failed to test {model_config['name']}: {str(e)}")
    
    # Summary report
    logger.info("\n" + "="*60)
    logger.info("📊 SUMMARY REPORT")
    logger.info("="*60)
    
    logger.info("\n🎯 Tool Calling Capability Summary:")
    logger.info("Model Size | Model Name | Tool Calling | Status")
    logger.info("-" * 60)
    
    for result in all_results:
        model = result["model"]
        if result["available"]:
            tool_status = "✅ Working" if result["tool_calling_success"] else "❌ Failed"
            status = "Available"
        else:
            tool_status = "N/A"
            status = "Not Pulled"
        
        logger.info(f"{model['size']:10} | {model['name']:20} | {tool_status:12} | {status}")
    
    logger.info("\n📈 Performance Metrics:")
    for result in all_results:
        if result["available"] and result["success_rate"] > 0:
            model_name = result["model"]["name"]
            success_rate = result["success_rate"]
            avg_time = result["avg_response_time"]
            errors = len(result["errors"])
            
            logger.info(f"\n{model_name}:")
            logger.info(f"  ✅ Success Rate: {success_rate:.1f}%")
            logger.info(f"  ⏱️  Avg Response Time: {avg_time:.2f}s")
            logger.info(f"  ❌ Errors: {errors}")
    
    # Find best performing model
    available_results = [r for r in all_results if r["available"] and r["success_rate"] > 0]
    if available_results:
        # Best for tool calling
        tool_calling_models = [r for r in available_results if r["tool_calling_success"]]
        if tool_calling_models:
            fastest_tool_model = min(tool_calling_models, key=lambda x: x["avg_response_time"])
            logger.info(f"\n🏆 Best Tool-Calling Model: {fastest_tool_model['model']['name']} ({fastest_tool_model['avg_response_time']:.2f}s avg)")
        
        # Fastest overall
        fastest_model = min(available_results, key=lambda x: x["avg_response_time"])
        logger.info(f"⚡ Fastest Model: {fastest_model['model']['name']} ({fastest_model['avg_response_time']:.2f}s avg)")
    
    logger.info("\n💡 Recommendations:")
    logger.info("- For production tool calling: Use 7B+ parameter models")
    logger.info("- For development/testing: Use mock mode with any model")
    logger.info("- For best performance: mistral:7b or llama3.1:8b")

if __name__ == "__main__":
    asyncio.run(main())