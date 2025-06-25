"""
System prompts for AWS Strands Weather Agent.

This package contains system prompts for different use cases:
- default.txt: Standard weather and agricultural assistant
- agriculture.txt: Specialized for agricultural queries
- simple.txt: Simplified for basic weather queries
"""

from .prompt_manager import PromptManager

__all__ = ["PromptManager"]