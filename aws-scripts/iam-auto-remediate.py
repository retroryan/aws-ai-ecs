#!/usr/bin/env python3
"""
AWS IAM Auto-Remediation Script

This script consumes the JSON output from a-iam-check.py and can automatically
execute the recommended security improvements.

Usage:
    # Generate JSON guide
    python a-iam-check.py --json-output > iam-guide.json
    
    # Review and execute recommendations
    python iam-auto-remediate.py --input iam-guide.json --dry-run
    python iam-auto-remediate.py --input iam-guide.json --execute
"""

import json
import sys
import subprocess
import argparse
from typing import Dict, List, Any
import boto3
from datetime import datetime

class IAMAutoRemediator:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.iam_client = boto3.client('iam')
        self.executed_commands = []
        self.failed_commands = []
        
    def load_json_guide(self, file_path: str) -> Dict[str, Any]:
        """Load the JSON remediation guide."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Failed to load JSON guide: {e}")
            sys.exit(1)
    
    def execute_aws_command(self, command: str, description: str = "") -> bool:
        """Execute an AWS CLI command."""
        if self.dry_run:
            print(f"🔍 DRY RUN: {command}")
            if description:
                print(f"   Purpose: {description}")
            return True
        
        try:
            print(f"🚀 Executing: {command}")
            if description:
                print(f"   Purpose: {description}")
            
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                check=True
            )
            
            print(f"✅ Success: {result.stdout.strip()}")
            self.executed_commands.append({
                "command": command,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "success": True
            })
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed: {e.stderr.strip()}")
            self.failed_commands.append({
                "command": command,
                "description": description,
                "error": e.stderr.strip(),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def validate_prerequisites(self, prerequisites: List[str]) -> bool:
        """Check if the current user has required permissions."""
        print(f"🔐 Checking prerequisites: {', '.join(prerequisites)}")
        
        # This is a simplified check - in production you'd want to use
        # IAM policy simulation or actual permission testing
        try:
            # Test basic IAM read access
            self.iam_client.get_user()
            print("✅ Basic IAM access confirmed")
            return True
        except Exception as e:
            print(f"❌ Permission check failed: {e}")
            return False
    
    def execute_action(self, action: Dict[str, Any]) -> bool:
        """Execute a single remediation action."""
        action_type = action.get('action_type')
        priority = action.get('priority')
        description = action.get('description')
        
        print(f"\n{'='*60}")
        print(f"🎯 ACTION: {action_type.upper()}")
        print(f"📊 Priority: {priority.upper()}")
        print(f"📝 Description: {description}")
        
        # Check prerequisites
        prerequisites = action.get('prerequisites', [])
        if prerequisites and not self.validate_prerequisites(prerequisites):
            print("⚠️  Skipping action due to insufficient permissions")
            return False
        
        # Execute AWS commands
        aws_commands = action.get('aws_commands', [])
        success_count = 0
        
        for cmd_info in aws_commands:
            command = cmd_info.get('command')
            cmd_description = cmd_info.get('note', cmd_info.get('description', ''))
            
            if self.execute_aws_command(command, cmd_description):
                success_count += 1
        
        # Show manual steps if any
        manual_steps = action.get('manual_steps', [])
        if manual_steps:
            print(f"\n📋 MANUAL STEPS REQUIRED:")
            for step in manual_steps:
                print(f"   • {step}")
        
        # Show validation commands
        validation = action.get('validation', {})
        if validation:
            print(f"\n🔍 VALIDATION:")
            check_cmd = validation.get('check_command')
            expected = validation.get('expected_result')
            if check_cmd:
                print(f"   Command: {check_cmd}")
                print(f"   Expected: {expected}")
        
        return success_count == len(aws_commands)
    
    def process_guide(self, guide: Dict[str, Any]):
        """Process the complete remediation guide."""
        metadata = guide.get('metadata', {})
        print(f"🛡️  IAM AUTO-REMEDIATION")
        print(f"Account: {metadata.get('account_id')}")
        print(f"Generated: {metadata.get('generated_at')}")
        print(f"Total Actions: {metadata.get('total_actions')}")
        
        if self.dry_run:
            print(f"\n🔍 DRY RUN MODE - No changes will be made")
        else:
            print(f"\n🚀 EXECUTION MODE - Changes will be applied")
        
        # Get execution plan
        execution_plan = guide.get('execution_plan', {})
        
        # Execute critical actions first
        critical_actions = execution_plan.get('critical_actions', [])
        if critical_actions:
            print(f"\n🔴 EXECUTING CRITICAL ACTIONS ({len(critical_actions)})")
            for action in critical_actions:
                self.execute_action(action)
        
        # Execute high priority actions
        high_actions = execution_plan.get('high_priority_actions', [])
        if high_actions:
            print(f"\n🟠 EXECUTING HIGH PRIORITY ACTIONS ({len(high_actions)})")
            for action in high_actions:
                self.execute_action(action)
        
        # Execute medium priority actions
        medium_actions = execution_plan.get('medium_priority_actions', [])
        if medium_actions:
            print(f"\n🟡 EXECUTING MEDIUM PRIORITY ACTIONS ({len(medium_actions)})")
            for action in medium_actions:
                self.execute_action(action)
        
        # Show summary
        self.show_summary(guide)
    
    def show_summary(self, guide: Dict[str, Any]):
        """Show execution summary."""
        print(f"\n{'='*60}")
        print(f"📊 EXECUTION SUMMARY")
        print(f"{'='*60}")
        
        print(f"✅ Successful commands: {len(self.executed_commands)}")
        print(f"❌ Failed commands: {len(self.failed_commands)}")
        
        if self.failed_commands:
            print(f"\n❌ FAILED COMMANDS:")
            for cmd in self.failed_commands:
                print(f"   • {cmd['command']}")
                print(f"     Error: {cmd['error']}")
        
        # Show validation commands
        validation_commands = guide.get('validation_commands', {})
        if validation_commands:
            print(f"\n🔍 VALIDATION COMMANDS:")
            for name, command in validation_commands.items():
                print(f"   • {name}: {command}")
        
        # Show rollback plan
        rollback_plan = guide.get('rollback_plan', {})
        if rollback_plan and (self.executed_commands or not self.dry_run):
            print(f"\n🔄 ROLLBACK COMMANDS (if needed):")
            for cmd_info in rollback_plan.get('commands', []):
                print(f"   • {cmd_info['action']}: {cmd_info['command']}")
        
        # Show best practices
        best_practices = guide.get('best_practices', {})
        if best_practices:
            print(f"\n💡 BEST PRACTICES TO REMEMBER:")
            for category, practices in best_practices.items():
                print(f"   {category.upper()}:")
                for practice in practices:
                    print(f"     • {practice}")

def main():
    parser = argparse.ArgumentParser(
        description="AWS IAM Auto-Remediation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate remediation guide
  python a-iam-check.py --json-output > iam-guide.json
  
  # Review recommendations (dry run)
  python iam-auto-remediate.py --input iam-guide.json --dry-run
  
  # Execute recommendations
  python iam-auto-remediate.py --input iam-guide.json --execute
  
  # Execute only high priority actions
  python iam-auto-remediate.py --input iam-guide.json --execute --priority high
        """
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Path to JSON remediation guide file'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Show what would be executed without making changes (default)'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the remediation commands'
    )
    
    parser.add_argument(
        '--priority',
        choices=['critical', 'high', 'medium', 'all'],
        default='all',
        help='Execute only actions of specified priority level'
    )
    
    args = parser.parse_args()
    
    # Determine execution mode
    dry_run = not args.execute
    
    if args.execute:
        confirm = input("⚠️  This will make changes to your AWS account. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    try:
        remediator = IAMAutoRemediator(dry_run=dry_run)
        guide = remediator.load_json_guide(args.input)
        remediator.process_guide(guide)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Remediation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Remediation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
