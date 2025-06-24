"""
Pydantic models for the AWS Strands Weather Agent.

This module provides the core structured response models used for
type-safe communication between the agent and API.
"""

from .structured_responses import (
    ExtractedLocation,
    WeatherDataSummary,
    AgriculturalAssessment,
    WeatherQueryResponse,
    ValidationResult,
)

__all__ = [
    # Structured response models
    "ExtractedLocation",
    "WeatherDataSummary",
    "AgriculturalAssessment",
    "WeatherQueryResponse",
    "ValidationResult",
]