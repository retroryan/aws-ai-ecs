#!/usr/bin/env python3
"""Debug telemetry configuration issues."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Load .env from parent directory
from dotenv import load_dotenv
env_path = parent_dir / '.env'
load_dotenv(env_path)

def check_environment():
    """Check all required environment variables."""
    required = {
        "LANGFUSE_PUBLIC_KEY": os.getenv("LANGFUSE_PUBLIC_KEY"),
        "LANGFUSE_SECRET_KEY": os.getenv("LANGFUSE_SECRET_KEY"),
        "LANGFUSE_HOST": os.getenv("LANGFUSE_HOST"),
        "BEDROCK_MODEL_ID": os.getenv("BEDROCK_MODEL_ID"),
        "BEDROCK_REGION": os.getenv("BEDROCK_REGION")
    }
    
    print("🔍 Environment Check:")
    all_set = True
    for key, value in required.items():
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"  ✅ {key}: {masked}")
        else:
            print(f"  ❌ {key}: NOT SET")
            all_set = False
    
    return all_set

def check_connectivity():
    """Test Langfuse connectivity."""
    import requests
    from base64 import b64encode
    
    host = os.getenv("LANGFUSE_HOST")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    
    if not all([host, public_key, secret_key]):
        print("  ❌ Missing credentials for connectivity test")
        return False
    
    auth = b64encode(f"{public_key}:{secret_key}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    
    try:
        resp = requests.get(f"{host}/api/public/health", headers=headers)
        if resp.status_code == 200:
            print(f"  ✅ Langfuse reachable: {resp.json()}")
            return True
        else:
            print(f"  ❌ Langfuse returned: {resp.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return False

def check_imports():
    """Test critical imports."""
    print("\n🔍 Import Check:")
    try:
        from strands.telemetry import StrandsTelemetry
        print("  ✅ StrandsTelemetry importable")
    except Exception as e:
        print(f"  ❌ StrandsTelemetry import failed: {e}")
        return False
    
    try:
        from weather_agent.langfuse_telemetry import LangfuseTelemetry
        print("  ✅ LangfuseTelemetry importable")
    except Exception as e:
        print(f"  ❌ LangfuseTelemetry import failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Langfuse Telemetry Debug Tool")
    print("=" * 50)
    
    env_ok = check_environment()
    import_ok = check_imports()
    
    if env_ok and import_ok:
        print("\n🔍 Connectivity Check:")
        conn_ok = check_connectivity()
        
        if conn_ok:
            print("\n✅ All checks passed! Telemetry should work.")
        else:
            print("\n⚠️  Connectivity issue detected.")
    else:
        print("\n❌ Fix environment/import issues first.")