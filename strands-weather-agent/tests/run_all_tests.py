#!/usr/bin/env python3
"""
Run all async tests for the AWS Strands + FastMCP Weather Agent in sequence.
This handles the async nature of the tests and provides a summary.
"""

import asyncio
import sys
import os
import time
from typing import List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import remaining test modules
from test_coordinates import test_coordinates_simple as test_coordinates
from test_mcp_agent_strands import test_basic_query, test_structured_output
from test_structured_output import test_structured_responses
from test_pydantic_validation import test_model_validation
from test_mcp_servers_pydantic import test_mcp_servers


async def run_test(test_name: str, test_func) -> Tuple[str, bool, float, Optional[str]]:
    """Run a single test and return results."""
    print(f"\n{'='*70}")
    print(f"🧪 Running: {test_name}")
    print(f"{'='*70}")
    
    start_time = time.time()
    error_msg = None
    success = False
    
    try:
        await test_func()
        success = True
        print(f"\n✅ {test_name} completed successfully")
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ {test_name} failed with error: {error_msg}")
    
    elapsed_time = time.time() - start_time
    return test_name, success, elapsed_time, error_msg


async def run_all_tests():
    """Run all tests and provide a summary."""
    print("🚀 Starting AWS Strands + FastMCP Weather Agent Test Suite")
    print("=" * 70)
    print("\n⚠️  Note: This will start MCP servers as subprocesses")
    print("⚠️  Some tests may take time due to API calls and LLM interactions\n")
    
    # Define all tests to run
    tests = [
        ("Coordinates Test", test_coordinates),
        ("Basic Agent Query Test", test_basic_query),
        ("Agent Structured Output Test", test_structured_output),
        ("Structured Responses Test", test_structured_responses),
        ("Pydantic Model Validation Test", test_model_validation),
        ("MCP Servers Integration Test", test_mcp_servers),
    ]
    
    results: List[Tuple[str, bool, float, Optional[str]]] = []
    total_start = time.time()
    
    # Run each test
    for test_name, test_func in tests:
        result = await run_test(test_name, test_func)
        results.append(result)
        
        # Brief pause between tests to let servers clean up
        await asyncio.sleep(2)
    
    total_time = time.time() - total_start
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, success, _, _ in results if success)
    failed = len(results) - passed
    
    print(f"\nTotal tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total time: {total_time:.2f}s")
    
    print("\nDetailed Results:")
    print("-" * 70)
    for name, success, elapsed, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {name:<40} | {elapsed:>6.2f}s")
        if error:
            print(f"       Error: {error}")
    
    print("\n" + "="*70)
    
    # Return exit code
    return 0 if failed == 0 else 1


def main():
    """Main entry point."""
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()