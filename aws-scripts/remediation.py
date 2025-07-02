#!/usr/bin/env python3
"""
IAM Remediation Script
Processes IAM findings from iam-check.py and offers to fix them
Supports both interactive and automated remediation modes
"""

import json
import sys
import boto3
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import argparse
from datetime import datetime
import time
import subprocess


class IAMRemediator:
    """Handles remediation of IAM security findings"""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.iam = boto3.client('iam')
        self.remediation_log = []
        self.executed_commands = []
        self.failed_commands = []
        
        # Auto-remediation patterns mapping
        self.auto_remediate_patterns = {
            'IAM-UNUSED-ROLE': True,
            'IAM-EMPTY-GROUP': False,
            'IAM-STALE-ROLE': False,
            'IAM-NO-PASSWORD-POLICY': False,
            'IAM-CROSS-ACCOUNT': False,
            'IAM-NO-MFA': False,
            'IAM-OLD-ACCESS-KEY': False,
            'IAM-MULTIPLE-ACCESS-KEYS': False
        }
        
        # Map finding IDs to remediation methods
        self.remediation_methods = {
            'IAM-UNUSED-ROLE': self.remediate_unused_role,
            'IAM-STALE-ROLE': self.remediate_stale_role,
            'IAM-EMPTY-GROUP': self.remediate_empty_group,
            'IAM-CROSS-ACCOUNT': self.remediate_cross_account,
            'IAM-NO-MFA': self.remediate_no_mfa,
            'IAM-OLD-ACCESS-KEY': self.remediate_old_access_key,
            'IAM-WEAK-PASSWORD-POLICY': self.remediate_password_policy
        }
        # Patterns for roles to skip - these are AWS-managed and cannot be deleted
        self.skip_role_patterns = [
            'AWSReservedSSO_',  # AWS SSO managed roles (e.g., AWSReservedSSO_AdministratorAccess_*)
            'aws-reserved/',     # AWS reserved path roles
            'cdk-',              # CDK bootstrap roles (have stack dependencies)
            'ecsTaskExecutionRole',  # ECS service-linked role
            'rds-monitoring-role',   # RDS service-linked role
            'AWSGlueServiceRole',    # Glue service-linked role
            'KinesisFirehoseServiceRole-',  # Kinesis service roles
            'AmazonRedshift-CommandsAccessRole-',  # Redshift service roles
            'AWSServiceRole',    # AWS service-linked roles
            'OrganizationAccountAccessRole',  # AWS Organizations role
        ]
        # Patterns for groups to skip
        self.skip_group_patterns = [
            'AWSSESSendingGroupDoNotRename',  # AWS SES protected group
        ]
        
    def load_findings(self, findings_file: str) -> Dict[str, Any]:
        """Load findings from JSON file"""
        with open(findings_file, 'r') as f:
            return json.load(f)
    
    def should_skip_role(self, role_name: str) -> bool:
        """Check if a role should be skipped based on patterns"""
        for pattern in self.skip_role_patterns:
            if pattern in role_name:
                return True
        return False
    
    def should_skip_group(self, group_name: str) -> bool:
        """Check if a group should be skipped based on patterns"""
        for pattern in self.skip_group_patterns:
            if pattern in group_name:
                return True
        return False
    
    def should_auto_remediate(self, finding_id: str) -> bool:
        """Check if a finding type should be auto-remediated"""
        for pattern, auto in self.auto_remediate_patterns.items():
            if finding_id.startswith(pattern):
                return auto
        return False
    
    def execute_aws_command(self, command: str, description: str = "") -> bool:
        """Execute an AWS CLI command with error handling"""
        if self.dry_run:
            print(f"[DRY RUN] Would execute: {command}")
            if description:
                print(f"   Purpose: {description}")
            return True
        
        try:
            if self.verbose:
                print(f"Executing: {command}")
            
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                check=True
            )
            
            if self.verbose:
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
    
    def prompt_user(self, finding: Dict[str, Any], recommendations: List[Dict[str, Any]] = None) -> str:
        """Prompt user for remediation decision"""
        print(f"\n{'='*80}")
        print(f"Finding: {finding['title']}")
        print(f"Severity: {finding['severity'].upper()}")
        print(f"Resource: {finding['resource']}")
        print(f"Description: {finding['description']}")
        print(f"Risk: {finding['risk']}")
        print(f"Recommendation: {finding['recommendation']}")
        
        # Show compliance references if available
        if 'compliance' in finding and finding['compliance']:
            print(f"Compliance: {', '.join(finding['compliance'])}")
        
        # Show remediation steps if available from recommendations
        if recommendations:
            related_rec = self.find_related_recommendation(finding, recommendations)
            if related_rec and 'remediation_steps' in related_rec:
                print(f"\nRemediation Steps:")
                for step in related_rec['remediation_steps'][:3]:  # Show first 3 steps
                    print(f"  {step['step_number']}. {step['description']}")
                    if step.get('estimated_time'):
                        print(f"     Time: {step['estimated_time']}")
        
        # Check if auto-remediation is available
        finding_type = finding['finding_id'].split('-')[0:3]
        finding_type = '-'.join(finding_type[:3])
        
        if self.should_auto_remediate(finding['finding_id']):
            print(f"\n[AUTO-REMEDIATION AVAILABLE]")
            response = input("Fix this issue? (y/n/skip/all): ").lower()
        else:
            response = input("\nFix this issue? (y/n/skip): ").lower()
        
        return response
    
    def find_related_recommendation(self, finding: Dict[str, Any], recommendations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find recommendation related to a specific finding"""
        finding_id = finding['finding_id']
        for rec in recommendations:
            if finding_id in rec.get('related_findings', []):
                return rec
        return None
    
    def remediate_unused_role(self, finding: Dict[str, Any]) -> bool:
        """Delete an unused IAM role"""
        role_name = finding['resource'].replace('Role: ', '')
        
        # Check if role should be skipped
        if self.should_skip_role(role_name):
            if role_name.startswith('AWSReservedSSO_'):
                print(f"⚠️  Skipping AWS SSO permission set role: {role_name}")
                print("   These roles are managed by AWS Identity Center and cannot be deleted directly")
            else:
                print(f"⚠️  Skipping protected role: {role_name}")
            return False
        
        try:
            if self.dry_run:
                print(f"[DRY RUN] Would delete role: {role_name}")
                return True
            
            # First, check if role is attached to any instance profiles
            try:
                instance_profiles = self.iam.list_instance_profiles_for_role(RoleName=role_name)
                for profile in instance_profiles['InstanceProfiles']:
                    self.iam.remove_role_from_instance_profile(
                        InstanceProfileName=profile['InstanceProfileName'],
                        RoleName=role_name
                    )
                    print(f"  - Removed from instance profile: {profile['InstanceProfileName']}")
            except Exception as e:
                if 'NoSuchEntity' not in str(e):
                    print(f"  - Instance profile error: {str(e)}")
            
            # Detach managed policies
            try:
                attached_policies = self.iam.list_attached_role_policies(RoleName=role_name)
                for policy in attached_policies['AttachedPolicies']:
                    self.iam.detach_role_policy(
                        RoleName=role_name,
                        PolicyArn=policy['PolicyArn']
                    )
                    print(f"  - Detached policy: {policy['PolicyName']}")
            except Exception as e:
                print(f"  - Note: {str(e)}")
            
            # Delete inline policies
            try:
                inline_policies = self.iam.list_role_policies(RoleName=role_name)
                for policy_name in inline_policies['PolicyNames']:
                    self.iam.delete_role_policy(
                        RoleName=role_name,
                        PolicyName=policy_name
                    )
                    print(f"  - Deleted inline policy: {policy_name}")
            except Exception as e:
                print(f"  - Note: {str(e)}")
            
            # Delete the role
            self.iam.delete_role(RoleName=role_name)
            print(f"✓ Successfully deleted unused role: {role_name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to delete role {role_name}: {str(e)}")
            return False
    
    def remediate_stale_role(self, finding: Dict[str, Any]) -> bool:
        """Handle stale role - same as unused role deletion"""
        return self.remediate_unused_role(finding)
    
    def remediate_empty_group(self, finding: Dict[str, Any]) -> bool:
        """Delete an empty IAM group"""
        group_name = finding['resource'].replace('Group: ', '')
        
        # Check if group should be skipped
        if self.should_skip_group(group_name):
            print(f"⚠️  Skipping protected group: {group_name}")
            return False
        
        try:
            if self.dry_run:
                print(f"[DRY RUN] Would delete group: {group_name}")
                return True
            
            # First, detach managed policies
            try:
                attached_policies = self.iam.list_attached_group_policies(GroupName=group_name)
                for policy in attached_policies['AttachedPolicies']:
                    self.iam.detach_group_policy(
                        GroupName=group_name,
                        PolicyArn=policy['PolicyArn']
                    )
                    print(f"  - Detached policy: {policy['PolicyName']}")
            except Exception as e:
                print(f"  - Note: {str(e)}")
            
            # Delete inline policies
            try:
                inline_policies = self.iam.list_group_policies(GroupName=group_name)
                for policy_name in inline_policies['PolicyNames']:
                    self.iam.delete_group_policy(
                        GroupName=group_name,
                        PolicyName=policy_name
                    )
                    print(f"  - Deleted inline policy: {policy_name}")
            except Exception as e:
                print(f"  - Note: {str(e)}")
            
            # Delete the group
            self.iam.delete_group(GroupName=group_name)
            print(f"✓ Successfully deleted empty group: {group_name}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to delete group {group_name}: {str(e)}")
            return False
    
    def remediate_cross_account(self, finding: Dict[str, Any]) -> bool:
        """Review cross-account access - requires manual review"""
        role_name = finding['resource'].replace('Role: ', '')
        
        # Extract account ID from description if available
        account_id = None
        if 'external account' in finding['description']:
            import re
            match = re.search(r'external account (\d+)', finding['description'])
            if match:
                account_id = match.group(1)
        
        print(f"\n⚠️  Cross-account access requires manual review")
        print(f"Role: {role_name}")
        if account_id:
            print(f"External Account: {account_id}")
        print(f"\nThis role allows access from an external AWS account.")
        print(f"Common reasons for cross-account roles:")
        print(f"  - Third-party integrations (Fivetran, Datadog, etc.)")
        print(f"  - Partner account access")
        print(f"  - Multi-account AWS organization access")
        print(f"\nTo review the trust policy:")
        print(f"  aws iam get-role --role-name {role_name} --query Role.AssumeRolePolicyDocument")
        print(f"\n⚡ Only delete if you're certain the external access is no longer needed!")
        return False
    
    def remediate_no_mfa(self, finding: Dict[str, Any]) -> bool:
        """Guide user to enable MFA - requires manual action"""
        user_name = finding['resource'].replace('User: ', '').split(',')[0]
        
        print(f"\n🔐 MFA Setup Required for User: {user_name}")
        print(f"\nMFA adds an extra layer of security to your AWS account.")
        print(f"\nSteps to enable MFA:")
        print(f"  1. Sign in to AWS Console as {user_name}")
        print(f"  2. Navigate to IAM > Users > {user_name}")
        print(f"  3. Click 'Security credentials' tab")
        print(f"  4. Click 'Manage' next to 'Assigned MFA device'")
        print(f"  5. Follow the wizard to set up virtual or hardware MFA")
        print(f"\nCLI command to check MFA status:")
        print(f"  aws iam list-mfa-devices --user-name {user_name}")
        
        # Log manual action required
        self.remediation_log.append({
            'finding_id': finding['finding_id'],
            'resource': finding['resource'],
            'action': 'manual-mfa-setup-required',
            'timestamp': datetime.utcnow().isoformat(),
            'instructions': f'Enable MFA for user {user_name}'
        })
        return False
    
    def remediate_old_access_key(self, finding: Dict[str, Any]) -> bool:
        """Guide user to rotate old access keys"""
        # Extract user and key info from finding
        resource_parts = finding['resource'].split(', ')
        user_name = resource_parts[0].replace('User: ', '')
        key_id = None
        
        if len(resource_parts) > 1:
            key_id = resource_parts[1].replace('Key: ', '')
        
        print(f"\n🔑 Access Key Rotation Required")
        print(f"User: {user_name}")
        if key_id:
            print(f"Key ID: {key_id}")
        
        print(f"\nSteps to rotate access key:")
        print(f"  1. Create new access key:")
        print(f"     aws iam create-access-key --user-name {user_name}")
        print(f"  2. Update applications with new key")
        print(f"  3. Test new key is working")
        print(f"  4. Deactivate old key:")
        if key_id:
            print(f"     aws iam update-access-key --user-name {user_name} --access-key-id {key_id} --status Inactive")
        print(f"  5. After verification, delete old key:")
        if key_id:
            print(f"     aws iam delete-access-key --user-name {user_name} --access-key-id {key_id}")
        
        confirm = input("\nMark this for manual remediation? (y/n): ").lower()
        if confirm == 'y':
            self.remediation_log.append({
                'finding_id': finding['finding_id'],
                'resource': finding['resource'],
                'action': 'manual-key-rotation-required',
                'timestamp': datetime.utcnow().isoformat(),
                'instructions': f'Rotate access key for user {user_name}'
            })
        return False
    
    def remediate_password_policy(self, finding: Dict[str, Any]) -> bool:
        """Update password policy to meet security standards"""
        print(f"\n🔒 Password Policy Update Required")
        print(f"\nCurrent password policy does not meet security standards.")
        print(f"\nRecommended password policy settings:")
        print(f"  - Minimum length: 14 characters")
        print(f"  - Require uppercase, lowercase, numbers, and symbols")
        print(f"  - Maximum age: 90 days")
        print(f"  - Password reuse prevention: 24 passwords")
        
        if not self.dry_run:
            update = input("\nUpdate password policy to recommended settings? (y/n): ").lower()
            if update == 'y':
                try:
                    self.iam.update_account_password_policy(
                        MinimumPasswordLength=14,
                        RequireSymbols=True,
                        RequireNumbers=True,
                        RequireUppercaseCharacters=True,
                        RequireLowercaseCharacters=True,
                        AllowUsersToChangePassword=True,
                        MaxPasswordAge=90,
                        PasswordReusePrevention=24,
                        HardExpiry=False
                    )
                    print("✅ Password policy updated successfully")
                    return True
                except Exception as e:
                    print(f"❌ Failed to update password policy: {str(e)}")
                    return False
        else:
            print("[DRY RUN] Would update password policy")
            return True
        
        return False
    
    def remediate_finding(self, finding: Dict[str, Any], recommendation: Optional[Dict[str, Any]] = None) -> bool:
        """Remediate a single finding based on its type"""
        finding_id = finding['finding_id']
        
        # Find the appropriate remediation method
        for pattern, method in self.remediation_methods.items():
            if finding_id.startswith(pattern):
                return method(finding)
        
        # If no specific remediation method, check if recommendation has steps
        if recommendation and recommendation.get('remediation_steps'):
            return self.execute_recommendation_steps(finding, recommendation)
        
        print(f"No automated remediation available for {finding['title']}")
        return False
    
    def execute_recommendation_steps(self, finding: Dict[str, Any], recommendation: Dict[str, Any]) -> bool:
        """Execute remediation steps from a recommendation"""
        print(f"\n📋 Executing remediation: {recommendation['title']}")
        
        steps = recommendation.get('remediation_steps', [])
        automated_steps = [s for s in steps if s.get('automation_safe', False)]
        
        if not automated_steps:
            print("No automated steps available. Manual intervention required.")
            for step in steps:
                print(f"  {step['step_number']}. {step['description']}")
            return False
        
        success_count = 0
        for step in automated_steps:
            print(f"\nStep {step['step_number']}: {step['description']}")
            
            # Check prerequisites
            if step.get('prerequisites'):
                print(f"Prerequisites: {', '.join(step['prerequisites'])}")
                if not self.dry_run:
                    confirm = input("Prerequisites met? (y/n): ").lower()
                    if confirm != 'y':
                        print("Skipping step due to unmet prerequisites")
                        continue
            
            # Execute commands
            for cmd in step.get('commands', []):
                if cmd.startswith('#') or cmd.startswith('Manual:'):
                    print(f"Manual action required: {cmd}")
                else:
                    if self.execute_aws_command(cmd, step['description']):
                        success_count += 1
            
            # Run validation if available
            if step.get('validation') and not self.dry_run:
                print("Running validation...")
                self.execute_aws_command(step['validation'], "Validation")
        
        return success_count > 0
    
    def process_findings(self, findings_file: str, auto_mode: bool = False, severity_filter: str = None, execution_plan: bool = False):
        """Process all findings and offer remediation"""
        data = self.load_findings(findings_file)
        findings = data.get('findings', [])
        recommendations = data.get('recommendations', [])
        
        print(f"\nLoaded {len(findings)} findings from {findings_file}")
        print(f"Account: {data['account_id']}")
        print(f"Analysis Date: {data['analysis_date']}")
        print(f"Security Score: {data['security_score']}/100")
        
        # Show findings by severity
        if 'findings_by_severity' in data:
            print(f"\nFindings by Severity:")
            for sev, count in data['findings_by_severity'].items():
                if count > 0:
                    print(f"  {sev.upper()}: {count}")
        
        # Filter by severity if requested
        if severity_filter:
            severity_order = ['critical', 'high', 'medium', 'low', 'info']
            if severity_filter.lower() in severity_order:
                min_severity_index = severity_order.index(severity_filter.lower())
                findings = [f for f in findings if severity_order.index(f.get('severity', 'info').lower()) <= min_severity_index]
                print(f"\nFiltered to {len(findings)} findings with severity {severity_filter} or higher")
        
        # Use execution plan if requested
        if execution_plan and 'execution_plan' in data:
            findings = self.get_findings_from_execution_plan(data['execution_plan'])
        
        # Group findings by type for auto-remediation
        unused_roles = [f for f in findings if f['finding_id'].startswith('IAM-UNUSED-ROLE')]
        
        if auto_mode and unused_roles:
            # Filter out protected roles
            deletable_roles = []
            protected_roles = []
            
            for finding in unused_roles:
                role_name = finding['resource'].replace('Role: ', '')
                if self.should_skip_role(role_name):
                    protected_roles.append(finding)
                else:
                    deletable_roles.append(finding)
            
            print(f"\n{'='*80}")
            print(f"AUTO-REMEDIATION MODE: Found {len(unused_roles)} unused roles")
            if protected_roles:
                print(f"  - {len(protected_roles)} protected roles will be skipped")
            print(f"  - {len(deletable_roles)} roles can be deleted")
            
            if deletable_roles:
                response = input(f"Auto-delete {len(deletable_roles)} unused roles? (y/n): ").lower()
                
                if response == 'y':
                    for finding in deletable_roles:
                        print(f"\nProcessing: {finding['title']}")
                        success = self.remediate_finding(finding)
                        self.remediation_log.append({
                            'finding_id': finding['finding_id'],
                            'resource': finding['resource'],
                            'action': 'auto-deleted' if success else 'failed',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        time.sleep(0.5)  # Rate limiting
            
            # Log skipped protected roles
            for finding in protected_roles:
                role_name = finding['resource'].replace('Role: ', '')
                action_type = 'skipped-sso' if role_name.startswith('AWSReservedSSO_') else 'skipped-protected'
                self.remediation_log.append({
                    'finding_id': finding['finding_id'],
                    'resource': finding['resource'],
                    'action': action_type,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Process remaining findings individually
        fixed_count = 0
        skipped_count = 0
        auto_all = False
        
        for finding in findings:
            # Skip if already processed in auto mode
            if auto_mode and finding['finding_id'].startswith('IAM-UNUSED-ROLE'):
                continue
            
            # Find related recommendation
            related_rec = self.find_related_recommendation(finding, recommendations)
            
            # Auto-process if auto_all is set and remediation is available
            if auto_all and self.should_auto_remediate(finding['finding_id']):
                response = 'y'
            else:
                response = self.prompt_user(finding, recommendations)
            
            if response == 'all':
                auto_all = True
                response = 'y'
            
            if response == 'skip':
                break
            elif response == 'y':
                print(f"\nRemediating: {finding['title']}...")
                success = self.remediate_finding(finding, related_rec)
                
                if success:
                    fixed_count += 1
                    self.remediation_log.append({
                        'finding_id': finding['finding_id'],
                        'resource': finding['resource'],
                        'action': 'fixed',
                        'severity': finding.get('severity', 'unknown'),
                        'timestamp': datetime.utcnow().isoformat()
                    })
                else:
                    self.remediation_log.append({
                        'finding_id': finding['finding_id'],
                        'resource': finding['resource'],
                        'action': 'failed',
                        'severity': finding.get('severity', 'unknown'),
                        'timestamp': datetime.utcnow().isoformat()
                    })
            else:
                skipped_count += 1
                self.remediation_log.append({
                    'finding_id': finding['finding_id'],
                    'resource': finding['resource'],
                    'action': 'skipped',
                    'severity': finding.get('severity', 'unknown'),
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Summary
        print(f"\n{'='*80}")
        print(f"REMEDIATION SUMMARY")
        print(f"Fixed: {fixed_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Total processed: {fixed_count + skipped_count}/{len(findings)}")
        
        # Provide guidance on common failures and skipped items
        failed_items = [log for log in self.remediation_log if log['action'] == 'failed']
        sso_items = [log for log in self.remediation_log if log['action'] == 'skipped-sso']
        protected_items = [log for log in self.remediation_log if log['action'] == 'skipped-protected']
        
        if sso_items:
            print(f"\n🔐 {len(sso_items)} AWS SSO permission set roles were skipped")
            print("   These are managed by AWS Identity Center and cannot be deleted directly")
        
        if protected_items:
            print(f"\n🛡️  {len(protected_items)} protected roles were skipped")
            print("   These include service-linked roles and CDK bootstrap roles")
        
        if failed_items:
            print(f"\n⚠️  {len(failed_items)} items failed to remediate")
            print("\nCommon reasons for failures:")
            print("  • CDK roles: Still referenced by CloudFormation stacks")
            print("  • Service roles: Still in use by AWS services (ECS, RDS, Glue, etc.)")
            print("  • Cross-account roles: Active third-party integrations")
            print("  • Protected resources: AWS-managed resources that cannot be deleted")
            print("\nTo investigate failures, check:")
            print("  • CloudFormation stacks using the roles")
            print("  • Active ECS tasks, RDS instances, or Glue jobs")
            print("  • Third-party service configurations")
        
        # Save remediation log
        if self.remediation_log:
            log_file = f"remediation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Group actions by severity for summary
            actions_by_severity = {}
            for action in self.remediation_log:
                severity = action.get('severity', 'unknown')
                if severity not in actions_by_severity:
                    actions_by_severity[severity] = {'fixed': 0, 'failed': 0, 'skipped': 0}
                action_type = action['action']
                if action_type in ['fixed', 'failed', 'skipped']:
                    actions_by_severity[severity][action_type] += 1
            
            with open(log_file, 'w') as f:
                json.dump({
                    'remediation_date': datetime.utcnow().isoformat(),
                    'findings_file': findings_file,
                    'dry_run': self.dry_run,
                    'total_actions': len(self.remediation_log),
                    'summary_by_severity': actions_by_severity,
                    'executed_commands': len(self.executed_commands),
                    'failed_commands': len(self.failed_commands),
                    'actions': self.remediation_log,
                    'commands': {
                        'executed': self.executed_commands,
                        'failed': self.failed_commands
                    }
                }, f, indent=2)
            print(f"\nRemediation log saved to: {log_file}")
    
    def get_findings_from_execution_plan(self, execution_plan: Dict[str, List]) -> List[Dict[str, Any]]:
        """Extract findings from execution plan organized by priority"""
        findings = []
        priority_order = ['critical', 'high', 'medium', 'low']
        
        for priority in priority_order:
            if priority in execution_plan:
                # The execution plan contains recommendations, we need to get related findings
                # This is a simplified approach - in practice you might need to cross-reference
                print(f"\nProcessing {priority.upper()} priority items...")
                
        return findings


def main():
    parser = argparse.ArgumentParser(
        description='Remediate IAM security findings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive remediation
  python remediation.py findings.json
  
  # Auto-remediate unused roles
  python remediation.py findings.json --auto
  
  # Dry run mode
  python remediation.py findings.json --dry-run
  
  # Process only critical and high severity findings
  python remediation.py findings.json --severity high
  
  # Use execution plan from iam-check.py
  python remediation.py findings.json --execution-plan
        """
    )
    parser.add_argument('findings_file', nargs='?', default='findings.json',
                       help='Path to findings JSON file (default: findings.json)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--auto', action='store_true',
                       help='Enable auto-remediation for unused roles')
    parser.add_argument('--severity', choices=['critical', 'high', 'medium', 'low'],
                       help='Minimum severity level to process')
    parser.add_argument('--execution-plan', action='store_true',
                       help='Use execution plan from findings file')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed command output')
    
    args = parser.parse_args()
    
    # Check if findings file exists
    if not Path(args.findings_file).exists():
        print(f"Error: Findings file '{args.findings_file}' not found")
        print("Run 'python iam-check.py --json --format pretty --output findings.json' first")
        sys.exit(1)
    
    # Initialize remediator
    remediator = IAMRemediator(dry_run=args.dry_run, verbose=args.verbose)
    
    if args.dry_run:
        print("*** DRY RUN MODE - No changes will be made ***")
    
    try:
        remediator.process_findings(
            args.findings_file, 
            auto_mode=args.auto,
            severity_filter=args.severity,
            execution_plan=args.execution_plan
        )
    except KeyboardInterrupt:
        print("\n\nRemediation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError during remediation: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()