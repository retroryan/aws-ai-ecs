#!/usr/bin/env python3
"""
Test Ollama Connectivity

Simple script to verify Ollama is running and has the required model.
"""

import sys
import requests
import json


def check_ollama_service():
    """Check if Ollama service is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def get_available_models():
    """Get list of available Ollama models."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        return []
    except requests.exceptions.RequestException:
        return []


def check_model_available(model_name):
    """Check if a specific model is available."""
    models = get_available_models()
    return any(model_name in model for model in models)


def test_model_generation(model_name="llama3.2:1b"):
    """Test if model can generate text."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": "Say hello",
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            return True, response.json().get('response', '')
        return False, f"Status code: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return False, str(e)


def main():
    """Run connectivity tests."""
    print("🔍 Ollama Connectivity Test\n")
    
    # Test 1: Service running
    print("1. Checking if Ollama service is running...")
    if not check_ollama_service():
        print("❌ Ollama is not running!")
        print("   Please start Ollama with: ollama serve")
        sys.exit(1)
    print("✅ Ollama service is running")
    
    # Test 2: List models
    print("\n2. Available models:")
    models = get_available_models()
    if not models:
        print("❌ No models found!")
        print("   Please pull a model with: ollama pull llama3.2:1b")
        sys.exit(1)
    
    for model in models:
        print(f"   - {model}")
    
    # Test 3: Check for required model
    required_model = "llama3.2:1b"
    print(f"\n3. Checking for required model '{required_model}'...")
    if not check_model_available(required_model):
        print(f"❌ Model '{required_model}' not found!")
        print(f"   Please pull it with: ollama pull {required_model}")
        # Don't exit, try with available model
        if models:
            required_model = models[0].split(':')[0]  # Use first available
            print(f"   Will try with available model: {models[0]}")
    else:
        print(f"✅ Model '{required_model}' is available")
    
    # Test 4: Test generation
    print(f"\n4. Testing text generation with '{required_model}'...")
    success, result = test_model_generation(required_model)
    if success:
        print(f"✅ Generation successful!")
        print(f"   Response: {result[:100]}...")
    else:
        print(f"❌ Generation failed: {result}")
        sys.exit(1)
    
    print("\n✅ All connectivity tests passed!")
    print(f"   You can now use Ollama with the '{required_model}' model")
    
    # Show connection info for use in code
    print("\n📋 Connection details:")
    print(f"   Host: http://localhost:11434")
    print(f"   Model: {required_model}")
    print(f"   Python import: from strands.models.ollama import OllamaModel")


if __name__ == "__main__":
    main()