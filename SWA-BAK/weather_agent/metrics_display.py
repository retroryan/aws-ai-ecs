"""
Simple metrics display for AWS Strands Weather Agent.

Formats performance metrics from EventLoopMetrics for terminal output.
"""
import os
from datetime import datetime
from typing import Optional
from strands.telemetry.metrics import EventLoopMetrics


def format_metrics(metrics: EventLoopMetrics) -> str:
    """
    Format AWS Strands metrics for terminal display.
    
    Args:
        metrics: The EventLoopMetrics from streaming stop event
        
    Returns:
        Formatted metrics string
    """
    # Extract metrics from EventLoopMetrics object
    total_tokens = metrics.accumulated_usage.get('totalTokens', 0)
    input_tokens = metrics.accumulated_usage.get('inputTokens', 0)
    output_tokens = metrics.accumulated_usage.get('outputTokens', 0)
    latency_ms = metrics.accumulated_metrics.get('latencyMs', 0)
    
    # Calculate derived metrics
    latency_sec = latency_ms / 1000.0
    throughput = total_tokens / latency_sec if latency_sec > 0 else 0
    
    # Get model info
    model_id = os.environ.get('BEDROCK_MODEL_ID', 'unknown')
    model_name = model_id.split('.')[-1].split('-v')[0] if '.' in model_id else model_id
    
    # Format output
    return f"""
📊 Performance Metrics:
   ├─ Tokens: {total_tokens} total ({input_tokens} input, {output_tokens} output)
   ├─ Latency: {latency_sec:.2f} seconds
   ├─ Throughput: {throughput:.0f} tokens/second
   ├─ Model: {model_name}
   └─ Cycles: {metrics.cycle_count}
"""


class SessionMetrics:
    """Aggregate metrics across multiple queries."""
    
    def __init__(self):
        self.queries = []
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_queries = 0
        self.start_time = None
    
    def add_query(self, metrics: EventLoopMetrics):
        """Add metrics from a query to the session totals."""
        if self.start_time is None:
            self.start_time = datetime.now()
        
        self.total_queries += 1
        self.total_tokens += metrics.accumulated_usage.get('totalTokens', 0)
        self.total_input_tokens += metrics.accumulated_usage.get('inputTokens', 0)
        self.total_output_tokens += metrics.accumulated_usage.get('outputTokens', 0)
    
    def get_summary(self) -> str:
        """Get session summary metrics."""
        if self.total_queries == 0:
            return "No queries processed yet."
        
        duration = (datetime.now() - self.start_time).total_seconds()
        avg_tokens = self.total_tokens / self.total_queries
        
        return f"""
📈 Session Summary:
   ├─ Total Queries: {self.total_queries}
   ├─ Total Tokens: {self.total_tokens} ({self.total_input_tokens} in, {self.total_output_tokens} out)
   ├─ Average Tokens/Query: {avg_tokens:.0f}
   └─ Session Duration: {duration:.0f} seconds
"""


def is_telemetry_enabled() -> bool:
    """Check if telemetry is configured."""
    # Check for Langfuse configuration
    if os.getenv('LANGFUSE_PUBLIC_KEY') and os.getenv('LANGFUSE_SECRET_KEY'):
        return True
    
    # Check for OTEL configuration
    if os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'):
        return True
    
    # Check if telemetry is explicitly enabled
    if os.getenv('ENABLE_TELEMETRY', '').lower() == 'true':
        return True
    
    return False