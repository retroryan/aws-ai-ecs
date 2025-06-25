"""
Model Provider Abstraction for Weather Agent

This module provides an abstraction layer for different model providers (AWS Bedrock, Ollama)
to enable model-agnostic operation of the weather agent.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Strands imports
from strands.models import BedrockModel
from strands.models.ollama import OllamaModel

logger = logging.getLogger(__name__)


class ModelProvider(ABC):
    """Abstract base class for model providers."""
    
    @abstractmethod
    def create_model(self) -> Any:
        """Create and return the model instance."""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get provider information."""
        pass
    
    @abstractmethod
    def get_model_id(self) -> str:
        """Get the model identifier."""
        pass


class BedrockProvider(ModelProvider):
    """AWS Bedrock model provider."""
    
    def __init__(self):
        """Initialize Bedrock provider with environment configuration."""
        self.model_id = os.getenv("BEDROCK_MODEL_ID", 
                                  "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
        self.region = os.getenv("BEDROCK_REGION", "us-west-2")
        self.temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0"))
        
        logger.info(f"Initialized BedrockProvider with model: {self.model_id}")
    
    def create_model(self) -> BedrockModel:
        """Create and return a Bedrock model instance."""
        return BedrockModel(
            model_id=self.model_id,
            region_name=self.region,
            temperature=self.temperature
        )
    
    def get_info(self) -> Dict[str, Any]:
        """Get Bedrock provider information."""
        return {
            "provider": "bedrock",
            "model_id": self.model_id,
            "region": self.region,
            "temperature": self.temperature,
            "api_type": "aws"
        }
    
    def get_model_id(self) -> str:
        """Get the Bedrock model identifier."""
        return self.model_id


class OllamaProvider(ModelProvider):
    """Ollama local model provider."""
    
    def __init__(self):
        """Initialize Ollama provider with environment configuration."""
        self.model_id = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "4096"))
        self.top_p = float(os.getenv("OLLAMA_TOP_P", "0.9"))
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        
        logger.info(f"Initialized OllamaProvider with model: {self.model_id}")
        logger.info(f"Ollama host: {self.host}")
    
    def create_model(self) -> OllamaModel:
        """Create and return an Ollama model instance."""
        return OllamaModel(
            model_id=self.model_id,
            host=self.host,
            params={
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "stream": True,  # Enable streaming for better UX
            },
            timeout=self.timeout
        )
    
    def get_info(self) -> Dict[str, Any]:
        """Get Ollama provider information."""
        return {
            "provider": "ollama",
            "model_id": self.model_id,
            "host": self.host,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "timeout": self.timeout,
            "api_type": "local"
        }
    
    def get_model_id(self) -> str:
        """Get the Ollama model identifier."""
        return self.model_id


def create_model_provider() -> ModelProvider:
    """
    Factory function to create the appropriate model provider based on environment configuration.
    
    Returns:
        ModelProvider instance (BedrockProvider or OllamaProvider)
        
    Raises:
        ValueError: If an unknown provider type is specified
    """
    provider_type = os.getenv("MODEL_PROVIDER", "bedrock").lower()
    
    if provider_type == "ollama":
        logger.info("Creating Ollama model provider")
        return OllamaProvider()
    elif provider_type == "bedrock":
        logger.info("Creating AWS Bedrock model provider")
        return BedrockProvider()
    else:
        raise ValueError(f"Unknown model provider: {provider_type}. Supported: 'bedrock', 'ollama'")


def test_provider_connectivity(provider: ModelProvider) -> bool:
    """
    Test if the model provider is accessible.
    
    Args:
        provider: The model provider to test
        
    Returns:
        True if provider is accessible, False otherwise
    """
    try:
        if isinstance(provider, OllamaProvider):
            # For Ollama, we could check if the service is running
            import requests
            try:
                response = requests.get(f"{provider.host}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = [m['name'] for m in response.json().get('models', [])]
                    if any(provider.model_id in model for model in models):
                        logger.info(f"✅ Ollama model {provider.model_id} is available")
                        return True
                    else:
                        logger.warning(f"❌ Ollama model {provider.model_id} not found. Available: {models}")
                        return False
                else:
                    logger.warning(f"❌ Ollama service returned status {response.status_code}")
                    return False
            except Exception as e:
                logger.error(f"❌ Failed to connect to Ollama: {e}")
                return False
                
        elif isinstance(provider, BedrockProvider):
            # For Bedrock, we assume it's available if credentials are configured
            # A more thorough check would involve making an API call
            try:
                import boto3
                client = boto3.client('bedrock-runtime', region_name=provider.region)
                # Just creating the client is often enough to validate credentials
                logger.info("✅ AWS Bedrock credentials appear to be configured")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to create Bedrock client: {e}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Error testing provider connectivity: {e}")
        return False