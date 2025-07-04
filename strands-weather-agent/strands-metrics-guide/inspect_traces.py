#!/usr/bin/env python3
"""Inspect recent Langfuse traces."""

import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from base64 import b64encode
import json
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

def get_recent_traces(hours=1):
    """Fetch traces from the last N hours."""
    host = os.getenv("LANGFUSE_HOST")
    auth = b64encode(
        f"{os.getenv('LANGFUSE_PUBLIC_KEY')}:"
        f"{os.getenv('LANGFUSE_SECRET_KEY')}".encode()
    ).decode()
    
    from_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    resp = requests.get(
        f"{host}/api/public/traces",
        headers={"Authorization": f"Basic {auth}"},
        params={
            "fromTimestamp": from_time.isoformat(),
            "limit": 50
        }
    )
    
    if resp.status_code == 200:
        return resp.json().get("data", [])
    return []

def analyze_traces(traces):
    """Analyze trace patterns."""
    print(f"\n📊 Found {len(traces)} traces")
    
    # Group by session
    sessions = {}
    for trace in traces:
        attrs = trace.get("metadata", {}).get("attributes", {})
        session_id = attrs.get("session.id", "unknown")
        sessions.setdefault(session_id, []).append(trace)
    
    print(f"\n📊 Sessions: {len(sessions)}")
    for sid, traces in sessions.items():
        print(f"  - {sid}: {len(traces)} traces")
    
    # Token usage
    total_tokens = sum(
        trace.get("usage", {}).get("total", 0) 
        for trace in traces
    )
    print(f"\n💰 Total tokens used: {total_tokens:,}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    env_path = parent_dir / '.env'
    load_dotenv(env_path)
    
    import argparse
    parser = argparse.ArgumentParser(description="Inspect recent Langfuse traces")
    parser.add_argument("--hours", type=int, default=1, help="Hours to look back (default: 1)")
    args = parser.parse_args()
    
    traces = get_recent_traces(hours=args.hours)
    analyze_traces(traces)