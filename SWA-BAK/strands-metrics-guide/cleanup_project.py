#!/usr/bin/env python3
"""
Project cleanup utility for the Weather Agent.

This script helps maintain the project by:
- Removing old log files
- Cleaning up test results
- Checking for common issues
- Suggesting improvements
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import argparse


class ProjectCleaner:
    """Utility class for cleaning up the Weather Agent project."""
    
    def __init__(self, project_root: Path, dry_run: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.issues_found = []
        self.files_to_clean = []
        
    def check_old_logs(self, days: int = 7):
        """Find log files older than specified days."""
        print(f"\n🔍 Checking for log files older than {days} days...")
        
        logs_dir = self.project_root / "logs"
        if not logs_dir.exists():
            print("   No logs directory found")
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        old_files = []
        
        for log_file in logs_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_date.timestamp():
                old_files.append(log_file)
                self.files_to_clean.append(log_file)
        
        if old_files:
            print(f"   Found {len(old_files)} old log files")
            for f in old_files[:5]:  # Show first 5
                print(f"     - {f.name}")
            if len(old_files) > 5:
                print(f"     ... and {len(old_files) - 5} more")
        else:
            print("   No old log files found")
    
    def check_test_results(self):
        """Find old test result files."""
        print("\n🔍 Checking for old test results...")
        
        test_results_dir = self.project_root / "test_results"
        if test_results_dir.exists():
            for result_file in test_results_dir.glob("*"):
                if result_file.is_file():
                    self.files_to_clean.append(result_file)
            
            if self.files_to_clean:
                print(f"   Found {len([f for f in self.files_to_clean if 'test_results' in str(f)])} test result files")
        else:
            print("   No test results directory found")
    
    def check_temp_files(self):
        """Find temporary files that should be cleaned."""
        print("\n🔍 Checking for temporary files...")
        
        temp_patterns = [
            "**/*.pyc",
            "**/__pycache__",
            "**/.pytest_cache",
            "**/.DS_Store",
            "**/.*~",
            "**/*.tmp"
        ]
        
        temp_files = []
        for pattern in temp_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() or file_path.is_dir():
                    temp_files.append(file_path)
                    self.files_to_clean.append(file_path)
        
        if temp_files:
            print(f"   Found {len(temp_files)} temporary files/directories")
        else:
            print("   No temporary files found")
    
    def check_code_issues(self):
        """Check for common code issues."""
        print("\n🔍 Checking for code issues...")
        
        issues = []
        
        # Check for hardcoded ports
        print("   Checking for hardcoded ports...")
        hardcoded_ports = self._find_pattern("7777|7778|7779|7780", "*.py")
        if hardcoded_ports:
            issues.append(f"Found {len(hardcoded_ports)} files with hardcoded ports")
            self.issues_found.extend([f"Hardcoded port in {f}" for f in hardcoded_ports[:3]])
        
        # Check for old model IDs without us. prefix
        print("   Checking for outdated model IDs...")
        old_models = self._find_pattern(
            r"anthropic\.claude-3-[^'\"]*(?<!us\.anthropic\.claude)", 
            "*.py"
        )
        if old_models:
            issues.append(f"Found {len(old_models)} files with old model IDs")
            self.issues_found.extend([f"Old model ID in {f}" for f in old_models[:3]])
        
        # Check for AWS credential exports in code
        print("   Checking for AWS credential exports...")
        aws_exports = self._find_pattern(
            "aws configure export-credentials", 
            "*.py"
        )
        if aws_exports:
            issues.append(f"Found {len(aws_exports)} files with AWS credential exports")
            self.issues_found.extend([f"AWS export in {f}" for f in aws_exports[:3]])
        
        if issues:
            print(f"   Found {len(issues)} types of issues")
        else:
            print("   No major issues found")
    
    def _find_pattern(self, pattern: str, file_pattern: str) -> list:
        """Find files containing a pattern."""
        import re
        
        matching_files = []
        for file_path in self.project_root.rglob(file_pattern):
            if file_path.is_file() and '.git' not in str(file_path):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    if re.search(pattern, content, re.IGNORECASE):
                        matching_files.append(file_path.relative_to(self.project_root))
                except Exception:
                    pass
        
        return matching_files
    
    def check_env_files(self):
        """Check for .env file issues."""
        print("\n🔍 Checking environment files...")
        
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"
        
        if env_file.exists() and env_example.exists():
            # Compare keys
            env_keys = set()
            example_keys = set()
            
            with open(env_file) as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        env_keys.add(key)
            
            with open(env_example) as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key = line.split('=')[0].strip()
                        example_keys.add(key)
            
            missing_keys = example_keys - env_keys
            extra_keys = env_keys - example_keys
            
            if missing_keys:
                print(f"   ⚠️  Missing keys in .env: {', '.join(missing_keys)}")
                self.issues_found.append(f"Missing env keys: {', '.join(missing_keys)}")
            
            if extra_keys:
                print(f"   ℹ️  Extra keys in .env: {', '.join(extra_keys)}")
        else:
            if not env_file.exists():
                print("   ⚠️  No .env file found")
                self.issues_found.append("No .env file found")
            if not env_example.exists():
                print("   ⚠️  No .env.example file found")
    
    def generate_report(self):
        """Generate a cleanup report."""
        print("\n" + "="*60)
        print("📊 CLEANUP REPORT")
        print("="*60)
        
        print(f"\n🗑️  Files to clean: {len(self.files_to_clean)}")
        if self.files_to_clean:
            total_size = sum(f.stat().st_size for f in self.files_to_clean if f.exists())
            print(f"   Total size: {total_size / 1024 / 1024:.2f} MB")
        
        print(f"\n⚠️  Issues found: {len(self.issues_found)}")
        for issue in self.issues_found[:10]:  # Show first 10
            print(f"   - {issue}")
        
        if len(self.issues_found) > 10:
            print(f"   ... and {len(self.issues_found) - 10} more")
        
        print("\n💡 Recommendations:")
        if self.files_to_clean:
            print("   - Run with --execute to clean files")
        if self.issues_found:
            print("   - Review and fix the identified issues")
            print("   - Use environment variables instead of hardcoded values")
            print("   - Update model IDs to use inference profiles (us. prefix)")
    
    def execute_cleanup(self):
        """Execute the cleanup (delete files)."""
        if self.dry_run:
            print("\n⚠️  Dry run mode - no files will be deleted")
            print("   Use --execute to actually delete files")
            return
        
        print("\n🗑️  Executing cleanup...")
        deleted_count = 0
        deleted_size = 0
        
        for file_path in self.files_to_clean:
            if file_path.exists():
                try:
                    size = file_path.stat().st_size
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                    else:
                        file_path.unlink()
                    deleted_count += 1
                    deleted_size += size
                    print(f"   ✅ Deleted: {file_path.relative_to(self.project_root)}")
                except Exception as e:
                    print(f"   ❌ Failed to delete {file_path}: {e}")
        
        print(f"\n✅ Deleted {deleted_count} files/directories")
        print(f"   Freed up {deleted_size / 1024 / 1024:.2f} MB")
    
    def run_full_check(self):
        """Run all checks."""
        print("🧹 Weather Agent Project Cleanup Utility")
        print("="*60)
        
        self.check_old_logs()
        self.check_test_results()
        self.check_temp_files()
        self.check_code_issues()
        self.check_env_files()
        
        self.generate_report()
        
        if self.files_to_clean and not self.dry_run:
            response = input("\n⚠️  Delete these files? (y/n): ")
            if response.lower() == 'y':
                self.execute_cleanup()
            else:
                print("Cleanup cancelled")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Weather Agent Project Cleanup Utility")
    parser.add_argument("--execute", action="store_true",
                        help="Actually delete files (default is dry run)")
    parser.add_argument("--days", type=int, default=7,
                        help="Delete logs older than this many days (default: 7)")
    parser.add_argument("--path", type=Path, default=Path(__file__).parent.parent,
                        help="Project root path")
    
    args = parser.parse_args()
    
    cleaner = ProjectCleaner(
        project_root=args.path,
        dry_run=not args.execute
    )
    
    cleaner.run_full_check()


if __name__ == "__main__":
    main()