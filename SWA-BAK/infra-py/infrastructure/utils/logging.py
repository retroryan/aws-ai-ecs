"""
Logging utilities for infrastructure scripts.
"""

import logging
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


# Create console instance
console = Console()


def setup_logging(level: str = 'INFO', use_rich: bool = True) -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        use_rich: Whether to use rich console handler
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('infra')
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    if use_rich:
        handler = RichHandler(console=console, rich_tracebacks=True)
        handler.setFormatter(logging.Formatter('%(message)s'))
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    
    logger.addHandler(handler)
    return logger


# Create default logger
logger = setup_logging()


def log_info(message: str) -> None:
    """Log info message with green [INFO] prefix."""
    console.print(f"[green][INFO][/green] {message}")


def log_warn(message: str) -> None:
    """Log warning message with yellow [WARN] prefix."""
    console.print(f"[yellow][WARN][/yellow] {message}")


def log_error(message: str) -> None:
    """Log error message with red [ERROR] prefix."""
    console.print(f"[red][ERROR][/red] {message}")


def log_step(message: str) -> None:
    """Log step message with blue [STEP] prefix."""
    console.print(f"[blue][STEP][/blue] {message}")


def print_section(title: str) -> None:
    """Print section header."""
    console.print()
    console.print(f"[blue]=== {title} ===[/blue]")
    console.print()


def get_timestamp() -> str:
    """Get current timestamp in standard format."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')