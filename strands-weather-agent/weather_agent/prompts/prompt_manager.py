"""
System prompt management for AWS Strands Weather Agent.

This module provides robust system prompt loading with:
- Fallback handling for missing files
- Environment variable configuration  
- Cached prompt loading for performance
- Validation and error handling
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages system prompts for the weather agent with robust fallback handling.
    
    Features:
    - Loads prompts from files in the prompts/ directory
    - Supports environment variable configuration
    - Caches loaded prompts for performance
    - Provides fallback prompts if files are missing
    - Validates prompt content
    """
    
    def __init__(self):
        self.prompts_dir = Path(__file__).parent
        self._prompt_cache: Dict[str, str] = {}
        self._available_prompts = self._discover_prompts()
        
        logger.debug(f"PromptManager initialized with prompts directory: {self.prompts_dir}")
        logger.debug(f"Available prompts: {list(self._available_prompts.keys())}")
    
    def _discover_prompts(self) -> Dict[str, Path]:
        """Discover available prompt files in the prompts directory."""
        available = {}
        
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory does not exist: {self.prompts_dir}")
            return available
        
        for prompt_file in self.prompts_dir.glob("*.txt"):
            prompt_name = prompt_file.stem
            available[prompt_name] = prompt_file
            logger.debug(f"Found prompt: {prompt_name} at {prompt_file}")
        
        return available
    
    def get_prompt(self, prompt_name: str = "agriculture_structured") -> str:
        """
        Get a system prompt by name with caching and fallback handling.
        
        Only supports 'simple_prompt' and 'agriculture_structured' prompts.
        
        Args:
            prompt_name: Name of the prompt to load (simple_prompt or agriculture_structured)
            
        Returns:
            The system prompt content as a string
            
        Raises:
            ValueError: If prompt_name is invalid
        """
        if not prompt_name:
            prompt_name = "agriculture_structured"
        
        # Only allow simple_prompt and agriculture_structured
        allowed_prompts = ["simple_prompt", "agriculture_structured"]
        if prompt_name not in allowed_prompts:
            logger.warning(f"Prompt '{prompt_name}' not allowed, using agriculture_structured")
            prompt_name = "agriculture_structured"
        
        # Return cached prompt if available
        if prompt_name in self._prompt_cache:
            logger.debug(f"Using cached prompt: {prompt_name}")
            return self._prompt_cache[prompt_name]
        
        # Try to load from file
        prompt_content = self._load_prompt_from_file(prompt_name)
        
        if prompt_content:
            # Cache the loaded prompt
            self._prompt_cache[prompt_name] = prompt_content
            logger.info(f"Loaded system prompt: {prompt_name}")
            return prompt_content
        
        # Fallback to agriculture_structured if requested prompt not found
        if prompt_name != "agriculture_structured":
            logger.warning(f"Prompt '{prompt_name}' not found, falling back to agriculture_structured")
            return self.get_prompt("agriculture_structured")
        
        # If agriculture_structured is missing, raise an error
        raise FileNotFoundError(f"Required prompt file 'agriculture_structured.txt' not found in {self.prompts_dir}")
    
    def _load_prompt_from_file(self, prompt_name: str) -> Optional[str]:
        """Load prompt content from file."""
        if prompt_name not in self._available_prompts:
            logger.debug(f"Prompt file not found: {prompt_name}")
            return None
        
        prompt_file = self._available_prompts[prompt_name]
        
        try:
            content = prompt_file.read_text(encoding='utf-8').strip()
            
            if not content:
                logger.warning(f"Prompt file is empty: {prompt_file}")
                return None
            
            # Basic validation
            if len(content) < 50:
                logger.warning(f"Prompt file seems too short: {prompt_file} ({len(content)} chars)")
            
            logger.debug(f"Successfully loaded prompt from: {prompt_file}")
            return content
            
        except Exception as e:
            logger.error(f"Error reading prompt file {prompt_file}: {e}")
            return None
    
    def get_available_prompts(self) -> list[str]:
        """Get list of available prompt names."""
        return list(self._available_prompts.keys())
    
    def reload_prompts(self):
        """Clear cache and reload prompts from disk."""
        self._prompt_cache.clear()
        self._available_prompts = self._discover_prompts()
        logger.info("Prompt cache cleared and prompts reloaded")
    
    def validate_prompt(self, prompt_name: str) -> bool:
        """
        Validate that a prompt exists and is loadable.
        
        Args:
            prompt_name: Name of the prompt to validate
            
        Returns:
            True if prompt is valid and loadable, False otherwise
        """
        try:
            content = self.get_prompt(prompt_name)
            return len(content) > 0
        except Exception as e:
            logger.error(f"Prompt validation failed for '{prompt_name}': {e}")
            return False