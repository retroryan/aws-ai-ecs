#!/usr/bin/env python3
"""
Compare test results between different environments to identify differences
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

def load_test_results(file_path):
    """Load test results from JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def compare_tests(env1_data, env2_data, env1_name, env2_name):
    """Compare test results between two environments"""
    print(f"\n🔍 Comparing {env1_name} vs {env2_name}")
    print("=" * 80)
    
    # Create test lookup dictionaries
    env1_tests = {t["test_name"]: t for t in env1_data["tests"]}
    env2_tests = {t["test_name"]: t for t in env2_data["tests"]}
    
    # Find differences
    all_test_names = set(env1_tests.keys()) | set(env2_tests.keys())
    
    differences = []
    
    for test_name in sorted(all_test_names):
        test1 = env1_tests.get(test_name)
        test2 = env2_tests.get(test_name)
        
        if not test1:
            differences.append({
                "test": test_name,
                "issue": f"Missing in {env1_name}"
            })
            continue
            
        if not test2:
            differences.append({
                "test": test_name,
                "issue": f"Missing in {env2_name}"
            })
            continue
        
        # Compare key metrics
        diff = {}
        
        # Success status
        if test1.get("success") != test2.get("success"):
            diff["success"] = {
                env1_name: test1.get("success"),
                env2_name: test2.get("success")
            }
        
        # Formatting errors
        fmt_err1 = test1.get("has_formatting_error", False)
        fmt_err2 = test2.get("has_formatting_error", False)
        if fmt_err1 != fmt_err2:
            diff["formatting_error"] = {
                env1_name: fmt_err1,
                env2_name: fmt_err2
            }
        
        # Technical errors
        tech_err1 = test1.get("has_technical_error", False)
        tech_err2 = test2.get("has_technical_error", False)
        if tech_err1 != tech_err2:
            diff["technical_error"] = {
                env1_name: tech_err1,
                env2_name: tech_err2
            }
        
        # Retry behavior
        retry1 = test1.get("retry_detected", False)
        retry2 = test2.get("retry_detected", False)
        if retry1 != retry2:
            diff["retry_behavior"] = {
                env1_name: retry1,
                env2_name: retry2
            }
        
        # Timeouts
        timeout1 = test1.get("timeout", False)
        timeout2 = test2.get("timeout", False)
        if timeout1 != timeout2:
            diff["timeout"] = {
                env1_name: timeout1,
                env2_name: timeout2
            }
        
        # Response time (significant difference)
        if "duration" in test1 and "duration" in test2:
            time_diff = abs(test1["duration"] - test2["duration"])
            if time_diff > 2.0:  # More than 2 second difference
                diff["response_time"] = {
                    env1_name: f"{test1['duration']:.2f}s",
                    env2_name: f"{test2['duration']:.2f}s",
                    "difference": f"{time_diff:.2f}s"
                }
        
        if diff:
            differences.append({
                "test": test_name,
                "differences": diff
            })
    
    return differences

def print_comparison_report(differences, env1_name, env2_name):
    """Print a formatted comparison report"""
    
    if not differences:
        print("\n✅ No significant differences found between environments!")
        return
    
    print(f"\n⚠️  Found {len(differences)} differences between {env1_name} and {env2_name}:\n")
    
    # Group by issue type
    formatting_errors = []
    technical_errors = []
    retry_behaviors = []
    timeouts = []
    response_times = []
    other = []
    
    for diff in differences:
        if "issue" in diff:
            other.append(diff)
        elif "differences" in diff:
            diffs = diff["differences"]
            if "formatting_error" in diffs:
                formatting_errors.append(diff)
            elif "technical_error" in diffs:
                technical_errors.append(diff)
            elif "retry_behavior" in diffs:
                retry_behaviors.append(diff)
            elif "timeout" in diffs:
                timeouts.append(diff)
            elif "response_time" in diffs:
                response_times.append(diff)
            else:
                other.append(diff)
    
    # Print grouped differences
    if formatting_errors:
        print("📝 Formatting Error Differences:")
        for item in formatting_errors:
            test_name = item["test"]
            diff = item["differences"]["formatting_error"]
            print(f"   {test_name}:")
            print(f"      {env1_name}: {'Has error' if diff[env1_name] else 'No error'}")
            print(f"      {env2_name}: {'Has error' if diff[env2_name] else 'No error'}")
    
    if technical_errors:
        print("\n🔧 Technical Error Differences:")
        for item in technical_errors:
            test_name = item["test"]
            diff = item["differences"]["technical_error"]
            print(f"   {test_name}:")
            print(f"      {env1_name}: {'Has error' if diff[env1_name] else 'No error'}")
            print(f"      {env2_name}: {'Has error' if diff[env2_name] else 'No error'}")
    
    if retry_behaviors:
        print("\n🔄 Retry Behavior Differences:")
        for item in retry_behaviors:
            test_name = item["test"]
            diff = item["differences"]["retry_behavior"]
            print(f"   {test_name}:")
            print(f"      {env1_name}: {'Retry detected' if diff[env1_name] else 'No retry'}")
            print(f"      {env2_name}: {'Retry detected' if diff[env2_name] else 'No retry'}")
    
    if timeouts:
        print("\n⏱️  Timeout Differences:")
        for item in timeouts:
            test_name = item["test"]
            diff = item["differences"]["timeout"]
            print(f"   {test_name}:")
            print(f"      {env1_name}: {'Timeout' if diff[env1_name] else 'Completed'}")
            print(f"      {env2_name}: {'Timeout' if diff[env2_name] else 'Completed'}")
    
    if response_times:
        print("\n⏱️  Response Time Differences (>2s):")
        for item in response_times:
            test_name = item["test"]
            diff = item["differences"]["response_time"]
            print(f"   {test_name}:")
            print(f"      {env1_name}: {diff[env1_name]}")
            print(f"      {env2_name}: {diff[env2_name]}")
            print(f"      Difference: {diff['difference']}")

def generate_summary(env1_data, env2_data, differences):
    """Generate a summary of the comparison"""
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    # Count issue types
    formatting_count = sum(1 for d in differences if "differences" in d and "formatting_error" in d["differences"])
    technical_count = sum(1 for d in differences if "differences" in d and "technical_error" in d["differences"])
    retry_count = sum(1 for d in differences if "differences" in d and "retry_behavior" in d["differences"])
    
    print(f"\nTotal differences found: {len(differences)}")
    if formatting_count > 0:
        print(f"- Formatting errors unique to one environment: {formatting_count}")
    if technical_count > 0:
        print(f"- Technical errors unique to one environment: {technical_count}")
    if retry_count > 0:
        print(f"- Retry behaviors unique to one environment: {retry_count}")
    
    # Key finding
    print("\n🔑 Key Finding:")
    if formatting_count > 0 or technical_count > 0:
        print("The coordinate formatting issue appears to be environment-specific!")
        print("This suggests a difference in:")
        print("- Library versions")
        print("- Environment variables")
        print("- Network/proxy configuration")
        print("- JSON serialization settings")
    else:
        print("Both environments show similar behavior.")

def main():
    parser = argparse.ArgumentParser(description="Compare test results between environments")
    parser.add_argument("file1", help="First test result file")
    parser.add_argument("file2", help="Second test result file")
    parser.add_argument("--save", help="Save comparison to file")
    
    args = parser.parse_args()
    
    # Load test results
    try:
        data1 = load_test_results(args.file1)
        data2 = load_test_results(args.file2)
    except Exception as e:
        print(f"Error loading test files: {e}")
        sys.exit(1)
    
    env1_name = data1["environment"]
    env2_name = data2["environment"]
    
    # Compare results
    differences = compare_tests(data1, data2, env1_name, env2_name)
    
    # Print report
    print_comparison_report(differences, env1_name, env2_name)
    
    # Generate summary
    generate_summary(data1, data2, differences)
    
    # Save if requested
    if args.save:
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "environments": {
                "env1": {
                    "name": env1_name,
                    "file": args.file1,
                    "url": data1["base_url"]
                },
                "env2": {
                    "name": env2_name,
                    "file": args.file2,
                    "url": data2["base_url"]
                }
            },
            "differences": differences
        }
        
        with open(args.save, 'w') as f:
            json.dump(comparison, f, indent=2)
        print(f"\n💾 Comparison saved to: {args.save}")

if __name__ == "__main__":
    main()