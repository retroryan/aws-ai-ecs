"""
Console output utilities using Rich.
"""

from typing import Any, Callable, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel


# Global console instance
console = Console()


class spinner:
    """Context manager for showing progress with spinner."""
    
    def __init__(self, description: str, transient: bool = True):
        """
        Initialize spinner context manager.
        
        Args:
            description: Description to show
            transient: Whether to remove spinner after completion
        """
        self.description = description
        self.transient = transient
        self.progress = None
        self.task = None
    
    def __enter__(self):
        """Start the spinner."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=self.transient
        )
        self.progress.start()
        self.task = self.progress.add_task(self.description, total=None)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the spinner."""
        if self.progress:
            if exc_type is None:
                self.progress.update(self.task, description=f"[green]✓[/green] {self.description}")
            else:
                self.progress.update(self.task, description=f"[red]✗[/red] {self.description}")
            self.progress.stop()
    
    def update(self, description: str):
        """Update the spinner description."""
        if self.progress and self.task is not None:
            self.progress.update(self.task, description=description)


def with_progress(description: str, func: Callable, *args, **kwargs) -> Any:
    """
    Execute a function with a progress spinner.
    
    Args:
        description: Description to show
        func: Function to execute
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function
    """
    with spinner(description):
        return func(*args, **kwargs)


def create_table(title: str, columns: list[tuple[str, dict]]) -> Table:
    """
    Create a styled table.
    
    Args:
        title: Table title
        columns: List of (name, style_dict) tuples
        
    Returns:
        Configured Table instance
    """
    table = Table(title=title, show_header=True, header_style="bold")
    
    for col_name, col_style in columns:
        table.add_column(col_name, **col_style)
    
    return table


def print_success(message: str) -> None:
    """Print a success message in a panel."""
    panel = Panel(
        message,
        title="✅ Success",
        title_align="left",
        border_style="green",
        padding=(1, 2)
    )
    console.print(panel)


def print_error(message: str) -> None:
    """Print an error message in a panel."""
    panel = Panel(
        message,
        title="❌ Error",
        title_align="left",
        border_style="red",
        padding=(1, 2)
    )
    console.print(panel)


def print_warning(message: str) -> None:
    """Print a warning message in a panel."""
    panel = Panel(
        message,
        title="⚠️  Warning",
        title_align="left",
        border_style="yellow",
        padding=(1, 2)
    )
    console.print(panel)


def confirm(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation.
    
    Args:
        message: Confirmation message
        default: Default response
        
    Returns:
        True if confirmed, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"
    response = console.input(f"[yellow]{message}{suffix}[/yellow] ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']