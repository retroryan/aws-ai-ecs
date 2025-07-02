#!/usr/bin/env python3
"""
AWS IAM Security Audit Script

This script performs a comprehensive security audit of your AWS IAM configuration,
following AWS best practices and security recommendations. It identifies potential
security risks and provides actionable recommendations.

Key Features:
- Detects root user usage and provides warnings
- Analyzes current user permissions and group memberships
- Identifies overprivileged users and groups
- Recommends least-privilege alternatives
- Provides step-by-step remediation guidance
- Checks for common security misconfigurations
- Generates JSON output for automation scripts

Based on AWS IAM Security Best Practices:
https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html
"""

import json
import sys
import boto3
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import re

class SecurityLevel(Enum):
    CRITICAL = "🔴 CRITICAL"
    HIGH = "🟠 HIGH"
    MEDIUM = "🟡 MEDIUM"
    LOW = "🟢 LOW"
    INFO = "ℹ️  INFO"

@dataclass
class SecurityFinding:
    level: SecurityLevel
    title: str
    description: str
    recommendation: str
    remediation_steps: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "level": self.level.name,
            "level_display": self.level.value,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "remediation_steps": self.remediation_steps
        }

@dataclass
class IAMUserAnalysis:
    user_name: str
    user_arn: str
    is_root: bool
    groups: List[str]
    attached_policies: List[str]
    inline_policies: List[str]
    access_keys: List[Dict]
    mfa_enabled: bool
    last_activity: Optional[datetime]
    permissions_summary: Dict
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "user_name": self.user_name,
            "user_arn": self.user_arn,
            "is_root": self.is_root,
            "groups": self.groups,
            "attached_policies": self.attached_policies,
            "inline_policies": self.inline_policies,
            "access_keys": [
                {
                    "access_key_id": key.get("AccessKeyId"),
                    "status": key.get("Status"),
                    "create_date": key.get("CreateDate").isoformat() if key.get("CreateDate") else None,
                    "age_days": (datetime.now(timezone.utc) - key.get("CreateDate")).days if key.get("CreateDate") else None
                }
                for key in self.access_keys
            ],
            "mfa_enabled": self.mfa_enabled,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "permissions_summary": self.permissions_summary
        }

class IAMSecurityAuditor:
    def __init__(self):
        """Initialize the IAM Security Auditor with AWS clients."""
        try:
            self.sts_client = boto3.client('sts')
            self.iam_client = boto3.client('iam')
            self.findings: List[SecurityFinding] = []
            
            # Get current identity
            self.current_identity = self.sts_client.get_caller_identity()
            self.account_id = self.current_identity['Account']
            self.current_arn = self.current_identity['Arn']
            
        except Exception as e:
            print(f"❌ Failed to initialize AWS clients: {e}")
            print("💡 Ensure AWS credentials are configured: aws configure")
            sys.exit(1)

    def is_root_user(self, arn: str) -> bool:
        """Check if the given ARN represents the root user."""
        return arn == f"arn:aws:iam::{self.account_id}:root"

    def analyze_current_user(self, quiet: bool = False) -> IAMUserAnalysis:
        """Analyze the current user's IAM configuration."""
        if not quiet:
            print("🔍 Analyzing current user identity...")
        
        current_arn = self.current_identity['Arn']
        is_root = self.is_root_user(current_arn)
        
        if is_root:
            # Root user analysis
            return IAMUserAnalysis(
                user_name="root",
                user_arn=current_arn,
                is_root=True,
                groups=[],
                attached_policies=["FullAdministratorAccess (implicit)"],
                inline_policies=[],
                access_keys=[],
                mfa_enabled=False,  # We can't check this programmatically
                last_activity=None,
                permissions_summary={"admin": True, "full_access": True}
            )
        
        # Extract user name from ARN
        user_name = current_arn.split('/')[-1]
        
        try:
            # Get user details
            user_response = self.iam_client.get_user(UserName=user_name)
            user = user_response['User']
            
            # Get groups
            groups_response = self.iam_client.list_groups_for_user(UserName=user_name)
            groups = [group['GroupName'] for group in groups_response['Groups']]
            
            # Get attached managed policies
            attached_policies_response = self.iam_client.list_attached_user_policies(UserName=user_name)
            attached_policies = [policy['PolicyName'] for policy in attached_policies_response['AttachedPolicies']]
            
            # Get inline policies
            inline_policies_response = self.iam_client.list_user_policies(UserName=user_name)
            inline_policies = inline_policies_response['PolicyNames']
            
            # Get access keys
            access_keys_response = self.iam_client.list_access_keys(UserName=user_name)
            access_keys = access_keys_response['AccessKeyMetadata']
            
            # Check MFA devices
            mfa_devices_response = self.iam_client.list_mfa_devices(UserName=user_name)
            mfa_enabled = len(mfa_devices_response['MFADevices']) > 0
            
            return IAMUserAnalysis(
                user_name=user_name,
                user_arn=current_arn,
                is_root=False,
                groups=groups,
                attached_policies=attached_policies,
                inline_policies=inline_policies,
                access_keys=access_keys,
                mfa_enabled=mfa_enabled,
                last_activity=user.get('PasswordLastUsed'),
                permissions_summary=self._analyze_permissions(user_name, groups, attached_policies, inline_policies)
            )
            
        except Exception as e:
            print(f"❌ Failed to analyze user {user_name}: {e}")
            sys.exit(1)

    def _analyze_permissions(self, user_name: str, groups: List[str], 
                           attached_policies: List[str], inline_policies: List[str]) -> Dict:
        """Analyze the effective permissions of a user."""
        permissions = {
            "admin_access": False,
            "high_privilege": False,
            "services_accessed": set(),
            "dangerous_permissions": []
        }
        
        # Check for admin policies
        admin_indicators = [
            "AdministratorAccess", "PowerUserAccess", "fulladmin", 
            "admin", "root", "superuser"
        ]
        
        all_policies = attached_policies + inline_policies + groups
        
        for policy in all_policies:
            policy_lower = policy.lower()
            if any(admin in policy_lower for admin in admin_indicators):
                permissions["admin_access"] = True
                permissions["high_privilege"] = True
                permissions["dangerous_permissions"].append(policy)
        
        # Check groups for admin access
        for group in groups:
            try:
                group_policies = self.iam_client.list_attached_group_policies(GroupName=group)
                for policy in group_policies['AttachedPolicies']:
                    if any(admin in policy['PolicyName'].lower() for admin in admin_indicators):
                        permissions["admin_access"] = True
                        permissions["high_privilege"] = True
                        permissions["dangerous_permissions"].append(f"Group: {group} -> {policy['PolicyName']}")
            except Exception:
                continue
        
        return permissions

    def audit_root_user_usage(self, user_analysis: IAMUserAnalysis):
        """Audit root user usage and provide recommendations."""
        if user_analysis.is_root:
            self.findings.append(SecurityFinding(
                level=SecurityLevel.CRITICAL,
                title="Root User Access Detected",
                description=(
                    "You are currently using the AWS account root user. This is a critical "
                    "security risk as the root user has unrestricted access to all AWS services "
                    "and billing information."
                ),
                recommendation=(
                    "Immediately stop using the root user for daily tasks. Create an administrative "
                    "IAM user with appropriate permissions instead."
                ),
                remediation_steps=[
                    "1. Create a new IAM user with administrative permissions",
                    "2. Add the user to an admin group (not direct policy attachment)",
                    "3. Enable MFA on the new administrative user",
                    "4. Test the new user's access",
                    "5. Stop using root user credentials",
                    "6. Secure root user with MFA and store credentials safely",
                    "7. Delete root user access keys if they exist"
                ]
            ))

    def audit_user_permissions(self, user_analysis: IAMUserAnalysis):
        """Audit user permissions for overprivileged access."""
        if not user_analysis.is_root and user_analysis.permissions_summary.get("admin_access"):
            self.findings.append(SecurityFinding(
                level=SecurityLevel.HIGH,
                title="Administrative Access Detected",
                description=(
                    f"User '{user_analysis.user_name}' has administrative access through: "
                    f"{', '.join(user_analysis.permissions_summary.get('dangerous_permissions', []))}"
                ),
                recommendation=(
                    "Review if full administrative access is necessary. Consider using "
                    "least-privilege permissions instead."
                ),
                remediation_steps=[
                    "1. Audit what AWS services this user actually needs",
                    "2. Create service-specific policies instead of admin access",
                    "3. Use IAM Access Analyzer to generate least-privilege policies",
                    "4. Test new permissions thoroughly",
                    "5. Remove administrative access once confirmed"
                ]
            ))

    def audit_mfa_configuration(self, user_analysis: IAMUserAnalysis):
        """Audit MFA configuration."""
        if not user_analysis.is_root and not user_analysis.mfa_enabled:
            self.findings.append(SecurityFinding(
                level=SecurityLevel.HIGH,
                title="MFA Not Enabled",
                description=(
                    f"Multi-Factor Authentication (MFA) is not enabled for user "
                    f"'{user_analysis.user_name}'. This significantly increases security risk."
                ),
                recommendation="Enable MFA immediately for all IAM users, especially those with elevated permissions.",
                remediation_steps=[
                    "1. Go to IAM Console → Users → [username] → Security credentials",
                    "2. Click 'Assign MFA device'",
                    "3. Choose Virtual MFA device (recommended)",
                    "4. Use an authenticator app (Google Authenticator, Authy, etc.)",
                    "5. Follow the setup wizard to complete MFA enrollment",
                    "6. Test MFA login to ensure it works"
                ]
            ))

    def audit_access_keys(self, user_analysis: IAMUserAnalysis):
        """Audit access key configuration."""
        if user_analysis.access_keys:
            old_keys = []
            for key in user_analysis.access_keys:
                age_days = (datetime.now(timezone.utc) - key['CreateDate']).days
                if age_days > 90:
                    old_keys.append((key['AccessKeyId'], age_days))
            
            if old_keys:
                self.findings.append(SecurityFinding(
                    level=SecurityLevel.MEDIUM,
                    title="Old Access Keys Detected",
                    description=(
                        f"Found {len(old_keys)} access keys older than 90 days. "
                        f"Old keys: {', '.join([f'{key[0]} ({key[1]} days)' for key in old_keys])}"
                    ),
                    recommendation="Rotate access keys regularly (every 90 days maximum).",
                    remediation_steps=[
                        "1. Create new access keys",
                        "2. Update applications/scripts with new keys",
                        "3. Test that everything works with new keys",
                        "4. Deactivate old keys",
                        "5. Monitor for any failures",
                        "6. Delete old keys after confirming no issues"
                    ]
                ))

    def analyze_groups_and_users(self, quiet: bool = False) -> Tuple[List[Dict], List[Dict]]:
        """Analyze all groups and users in the account."""
        if not quiet:
            print("🔍 Analyzing all IAM groups and users...")
        
        # Get all groups
        groups = []
        try:
            paginator = self.iam_client.get_paginator('list_groups')
            for page in paginator.paginate():
                for group in page['Groups']:
                    # Get group policies
                    attached_policies = self.iam_client.list_attached_group_policies(
                        GroupName=group['GroupName']
                    )['AttachedPolicies']
                    
                    inline_policies = self.iam_client.list_group_policies(
                        GroupName=group['GroupName']
                    )['PolicyNames']
                    
                    # Get group members
                    members = self.iam_client.get_group(
                        GroupName=group['GroupName']
                    )['Users']
                    
                    groups.append({
                        'name': group['GroupName'],
                        'arn': group['Arn'],
                        'attached_policies': [p['PolicyName'] for p in attached_policies],
                        'inline_policies': inline_policies,
                        'members': [u['UserName'] for u in members],
                        'member_count': len(members)
                    })
        except Exception as e:
            print(f"⚠️  Warning: Could not analyze groups: {e}")
        
        # Get all users
        users = []
        try:
            paginator = self.iam_client.get_paginator('list_users')
            for page in paginator.paginate():
                for user in page['Users']:
                    # Get user groups
                    user_groups = self.iam_client.list_groups_for_user(
                        UserName=user['UserName']
                    )['Groups']
                    
                    # Get user policies
                    attached_policies = self.iam_client.list_attached_user_policies(
                        UserName=user['UserName']
                    )['AttachedPolicies']
                    
                    inline_policies = self.iam_client.list_user_policies(
                        UserName=user['UserName']
                    )['PolicyNames']
                    
                    users.append({
                        'name': user['UserName'],
                        'arn': user['Arn'],
                        'groups': [g['GroupName'] for g in user_groups],
                        'attached_policies': [p['PolicyName'] for p in attached_policies],
                        'inline_policies': inline_policies,
                        'last_used': user.get('PasswordLastUsed'),
                        'created': user['CreateDate']
                    })
        except Exception as e:
            print(f"⚠️  Warning: Could not analyze users: {e}")
        
        return groups, users

    def generate_json_remediation_guide(self, user_analysis: IAMUserAnalysis, 
                                       groups: List[Dict], users: List[Dict]) -> Dict[str, Any]:
        """Generate a comprehensive JSON guide for automated remediation."""
        
        # Determine recommended actions based on findings
        actions = []
        
        # Root user remediation
        if user_analysis.is_root:
            actions.append({
                "action_type": "create_admin_user",
                "priority": "critical",
                "description": "Create administrative IAM user to replace root user usage",
                "aws_commands": [
                    {
                        "service": "iam",
                        "operation": "create-user",
                        "parameters": {
                            "user-name": "admin-user"
                        },
                        "command": "aws iam create-user --user-name admin-user"
                    },
                    {
                        "service": "iam", 
                        "operation": "create-login-profile",
                        "parameters": {
                            "user-name": "admin-user",
                            "password": "TempPassword123!",
                            "password-reset-required": True
                        },
                        "command": "aws iam create-login-profile --user-name admin-user --password 'TempPassword123!' --password-reset-required"
                    }
                ],
                "prerequisites": ["iam:CreateUser", "iam:CreateLoginProfile"],
                "validation": {
                    "check_command": "aws iam get-user --user-name admin-user",
                    "expected_result": "User exists"
                }
            })
        
        # MFA remediation
        if not user_analysis.is_root and not user_analysis.mfa_enabled:
            actions.append({
                "action_type": "enable_mfa",
                "priority": "high",
                "description": f"Enable MFA for user {user_analysis.user_name}",
                "aws_commands": [
                    {
                        "service": "iam",
                        "operation": "create-virtual-mfa-device",
                        "parameters": {
                            "virtual-mfa-device-name": f"{user_analysis.user_name}-mfa"
                        },
                        "command": f"aws iam create-virtual-mfa-device --virtual-mfa-device-name {user_analysis.user_name}-mfa"
                    }
                ],
                "manual_steps": [
                    "Use AWS Console: IAM → Users → Security credentials → Assign MFA device",
                    "Scan QR code with authenticator app",
                    "Enter two consecutive MFA codes to complete setup"
                ],
                "prerequisites": ["iam:CreateVirtualMFADevice", "iam:EnableMFADevice"],
                "validation": {
                    "check_command": f"aws iam list-mfa-devices --user-name {user_analysis.user_name}",
                    "expected_result": "MFA device listed"
                }
            })
        
        # Admin access remediation
        if not user_analysis.is_root and user_analysis.permissions_summary.get("admin_access"):
            actions.append({
                "action_type": "create_least_privilege_user",
                "priority": "high", 
                "description": "Create least-privilege user for daily tasks",
                "aws_commands": [
                    {
                        "service": "iam",
                        "operation": "create-user",
                        "parameters": {
                            "user-name": "developer-user"
                        },
                        "command": "aws iam create-user --user-name developer-user"
                    },
                    {
                        "service": "iam",
                        "operation": "attach-user-policy", 
                        "parameters": {
                            "user-name": "developer-user",
                            "policy-arn": "arn:aws:iam::aws:policy/PowerUserAccess"
                        },
                        "command": "aws iam attach-user-policy --user-name developer-user --policy-arn arn:aws:iam::aws:policy/PowerUserAccess"
                    }
                ],
                "alternatives": [
                    {
                        "description": "Use service-specific policies instead",
                        "example_policies": [
                            "arn:aws:iam::aws:policy/AmazonS3FullAccess",
                            "arn:aws:iam::aws:policy/AmazonEC2FullAccess",
                            "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
                        ]
                    }
                ],
                "prerequisites": ["iam:CreateUser", "iam:AttachUserPolicy"],
                "validation": {
                    "check_command": "aws iam list-attached-user-policies --user-name developer-user",
                    "expected_result": "PowerUserAccess policy attached"
                }
            })
        
        # Access key rotation
        old_keys = []
        for key in user_analysis.access_keys:
            if key.get('CreateDate'):
                age_days = (datetime.now(timezone.utc) - key['CreateDate']).days
                if age_days > 90:
                    old_keys.append({
                        "access_key_id": key['AccessKeyId'],
                        "age_days": age_days,
                        "status": key.get('Status', 'Unknown')
                    })
        
        if old_keys:
            actions.append({
                "action_type": "rotate_access_keys",
                "priority": "medium",
                "description": f"Rotate {len(old_keys)} old access keys",
                "old_keys": old_keys,
                "aws_commands": [
                    {
                        "service": "iam",
                        "operation": "create-access-key",
                        "parameters": {
                            "user-name": user_analysis.user_name
                        },
                        "command": f"aws iam create-access-key --user-name {user_analysis.user_name}"
                    }
                ],
                "manual_steps": [
                    "1. Create new access key",
                    "2. Update applications with new credentials", 
                    "3. Test applications work with new keys",
                    "4. Deactivate old keys",
                    "5. Monitor for failures",
                    "6. Delete old keys after confirmation"
                ],
                "prerequisites": ["iam:CreateAccessKey", "iam:UpdateAccessKey", "iam:DeleteAccessKey"],
                "cleanup_commands": [
                    {
                        "description": "Delete old access key after validation",
                        "command": f"aws iam delete-access-key --user-name {user_analysis.user_name} --access-key-id <OLD_KEY_ID>",
                        "warning": "Only run after confirming new keys work"
                    }
                ]
            })
        
        # Group management recommendations
        admin_groups = [g for g in groups if any('admin' in p.lower() for p in g.get('attached_policies', []))]
        
        if admin_groups and not user_analysis.is_root:
            best_admin_group = admin_groups[0]  # Use first available admin group
            actions.append({
                "action_type": "use_admin_group",
                "priority": "medium",
                "description": f"Add administrative user to existing admin group: {best_admin_group['name']}",
                "aws_commands": [
                    {
                        "service": "iam",
                        "operation": "add-user-to-group",
                        "parameters": {
                            "group-name": best_admin_group['name'],
                            "user-name": "admin-user"
                        },
                        "command": f"aws iam add-user-to-group --group-name {best_admin_group['name']} --user-name admin-user"
                    }
                ],
                "prerequisites": ["iam:AddUserToGroup"],
                "validation": {
                    "check_command": f"aws iam get-group --group-name {best_admin_group['name']}",
                    "expected_result": "admin-user listed in group members"
                }
            })
        elif not admin_groups:
            actions.append({
                "action_type": "create_admin_group",
                "priority": "medium", 
                "description": "Create administrative group for better permission management",
                "aws_commands": [
                    {
                        "service": "iam",
                        "operation": "create-group",
                        "parameters": {
                            "group-name": "AdminGroup"
                        },
                        "command": "aws iam create-group --group-name AdminGroup"
                    },
                    {
                        "service": "iam",
                        "operation": "attach-group-policy",
                        "parameters": {
                            "group-name": "AdminGroup",
                            "policy-arn": "arn:aws:iam::aws:policy/AdministratorAccess"
                        },
                        "command": "aws iam attach-group-policy --group-name AdminGroup --policy-arn arn:aws:iam::aws:policy/AdministratorAccess"
                    }
                ],
                "prerequisites": ["iam:CreateGroup", "iam:AttachGroupPolicy"],
                "validation": {
                    "check_command": "aws iam list-attached-group-policies --group-name AdminGroup",
                    "expected_result": "AdministratorAccess policy attached"
                }
            })
        
        # Root user security actions
        root_security_actions = {
            "action_type": "secure_root_user",
            "priority": "critical",
            "description": "Secure the root user account",
            "manual_steps": [
                "Enable MFA on root user account",
                "Delete any root user access keys",
                "Store root credentials in secure location",
                "Document root user password recovery process"
            ],
            "aws_commands": [
                {
                    "service": "iam",
                    "operation": "list-access-keys",
                    "parameters": {},
                    "command": "aws iam list-access-keys",
                    "note": "Check for root user access keys to delete"
                }
            ],
            "validation": {
                "manual_check": "Verify MFA is enabled on root user in AWS Console",
                "command_check": "aws iam list-access-keys should return empty for root user"
            }
        }
        
        if user_analysis.is_root or any(f.level == SecurityLevel.CRITICAL for f in self.findings):
            actions.append(root_security_actions)
        
        # Generate the complete JSON structure
        json_guide = {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "account_id": self.account_id,
                "current_user": user_analysis.user_name,
                "current_user_arn": user_analysis.user_arn,
                "audit_version": "1.0",
                "total_actions": len(actions)
            },
            "current_state": {
                "user_analysis": user_analysis.to_dict(),
                "security_findings": [finding.to_dict() for finding in self.findings],
                "groups_summary": {
                    "total_groups": len(groups),
                    "admin_groups": [g['name'] for g in groups if any('admin' in p.lower() for p in g.get('attached_policies', []))],
                    "groups_with_members": [g['name'] for g in groups if g.get('member_count', 0) > 0]
                },
                "users_summary": {
                    "total_users": len(users),
                    "users_with_groups": [u['name'] for u in users if u.get('groups')],
                    "users_with_policies": [u['name'] for u in users if u.get('attached_policies') or u.get('inline_policies')]
                }
            },
            "recommended_actions": actions,
            "execution_plan": {
                "critical_actions": [a for a in actions if a.get('priority') == 'critical'],
                "high_priority_actions": [a for a in actions if a.get('priority') == 'high'],
                "medium_priority_actions": [a for a in actions if a.get('priority') == 'medium'],
                "execution_order": [
                    "1. Execute critical actions first (root user issues)",
                    "2. Enable MFA on all users",
                    "3. Create least-privilege users",
                    "4. Rotate old access keys",
                    "5. Organize users into appropriate groups"
                ]
            },
            "required_permissions": {
                "minimum_permissions": [
                    "iam:CreateUser",
                    "iam:CreateGroup", 
                    "iam:AttachUserPolicy",
                    "iam:AttachGroupPolicy",
                    "iam:AddUserToGroup",
                    "iam:CreateAccessKey",
                    "iam:DeleteAccessKey",
                    "iam:CreateVirtualMFADevice",
                    "iam:EnableMFADevice"
                ],
                "read_permissions": [
                    "iam:GetUser",
                    "iam:ListUsers",
                    "iam:ListGroups",
                    "iam:ListGroupsForUser",
                    "iam:ListAttachedUserPolicies",
                    "iam:ListUserPolicies",
                    "iam:ListAccessKeys",
                    "iam:ListMFADevices"
                ]
            },
            "validation_commands": {
                "verify_user_creation": "aws iam get-user --user-name <username>",
                "verify_group_membership": "aws iam get-group --group-name <groupname>",
                "verify_policy_attachment": "aws iam list-attached-user-policies --user-name <username>",
                "verify_mfa_enabled": "aws iam list-mfa-devices --user-name <username>",
                "verify_access_keys": "aws iam list-access-keys --user-name <username>"
            },
            "rollback_plan": {
                "description": "Commands to rollback changes if needed",
                "commands": [
                    {
                        "action": "Remove user from group",
                        "command": "aws iam remove-user-from-group --group-name <groupname> --user-name <username>"
                    },
                    {
                        "action": "Detach policy from user",
                        "command": "aws iam detach-user-policy --user-name <username> --policy-arn <policy-arn>"
                    },
                    {
                        "action": "Delete user (after removing all attachments)",
                        "command": "aws iam delete-user --user-name <username>"
                    }
                ]
            },
            "best_practices": {
                "root_user": [
                    "Never use root user for daily tasks",
                    "Enable MFA on root user",
                    "Delete root user access keys",
                    "Store root credentials securely"
                ],
                "iam_users": [
                    "Enable MFA on all users",
                    "Use groups for permission management",
                    "Apply least privilege principle",
                    "Rotate access keys regularly"
                ],
                "groups": [
                    "Use groups instead of direct policy attachment",
                    "Create role-based groups (Admin, Developer, ReadOnly)",
                    "Regularly audit group memberships"
                ]
            }
        }
        
        return json_guide

    def recommend_non_root_setup(self, groups: List[Dict], users: List[Dict]):
        """Provide recommendations for proper non-root user setup."""
        print("\n" + "="*80)
        print("🎯 RECOMMENDATIONS FOR SECURE IAM SETUP")
        print("="*80)
        
        # Find admin groups
        admin_groups = []
        for group in groups:
            group_policies = group['attached_policies'] + group['inline_policies']
            if any('admin' in policy.lower() or 'administrator' in policy.lower() 
                   for policy in group_policies):
                admin_groups.append(group)
        
        print("\n📋 CURRENT ACCOUNT OVERVIEW:")
        print(f"   • Account ID: {self.account_id}")
        print(f"   • Total Users: {len(users)}")
        print(f"   • Total Groups: {len(groups)}")
        print(f"   • Admin Groups Found: {len(admin_groups)}")
        
        if admin_groups:
            print(f"\n🔑 EXISTING ADMIN GROUPS:")
            for group in admin_groups:
                print(f"   • {group['name']} ({group['member_count']} members)")
                for policy in group['attached_policies']:
                    print(f"     - Policy: {policy}")
        
        print(f"\n💡 RECOMMENDED SETUP STRATEGY:")
        
        if not admin_groups:
            print("   1️⃣  CREATE ADMIN GROUP (Recommended)")
            print("      aws iam create-group --group-name AdminGroup")
            print("      aws iam attach-group-policy --group-name AdminGroup \\")
            print("          --policy-arn arn:aws:iam::aws:policy/AdministratorAccess")
        else:
            print(f"   1️⃣  USE EXISTING ADMIN GROUP: {admin_groups[0]['name']}")
        
        print("\n   2️⃣  CREATE ADMINISTRATIVE USER")
        print("      aws iam create-user --user-name admin-user")
        print("      aws iam create-login-profile --user-name admin-user \\")
        print("          --password 'TempPassword123!' --password-reset-required")
        
        if admin_groups:
            print(f"      aws iam add-user-to-group --user-name admin-user \\")
            print(f"          --group-name {admin_groups[0]['name']}")
        else:
            print("      aws iam add-user-to-group --user-name admin-user \\")
            print("          --group-name AdminGroup")
        
        print("\n   3️⃣  ENABLE MFA FOR ADMIN USER")
        print("      # Use AWS Console: IAM → Users → admin-user → Security credentials → Assign MFA")
        
        print("\n   4️⃣  CREATE LEAST-PRIVILEGE USERS FOR DAILY TASKS")
        print("      # Example: Developer user")
        print("      aws iam create-user --user-name developer-user")
        print("      aws iam attach-user-policy --user-name developer-user \\")
        print("          --policy-arn arn:aws:iam::aws:policy/PowerUserAccess")
        
        print("\n   5️⃣  SECURE THE ROOT USER")
        print("      • Enable MFA on root user")
        print("      • Delete root user access keys")
        print("      • Store root credentials securely")
        print("      • Only use root for tasks that require it")
        
        print("\n🚨 ROOT USER TASKS (Only use root for these):")
        print("   • Change account settings (name, email, password)")
        print("   • Close AWS account")
        print("   • Change AWS support plan")
        print("   • Configure MFA delete for S3 buckets")
        print("   • Submit reverse DNS requests")
        print("   • Create CloudFront key pairs")

    def generate_security_report(self):
        """Generate a comprehensive security report."""
        print("\n" + "="*80)
        print("🛡️  AWS IAM SECURITY AUDIT REPORT")
        print("="*80)
        print(f"Account: {self.account_id}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Current Identity: {self.current_arn}")
        
        if not self.findings:
            print("\n✅ No security issues found! Your IAM configuration looks good.")
            return
        
        # Group findings by severity
        critical = [f for f in self.findings if f.level == SecurityLevel.CRITICAL]
        high = [f for f in self.findings if f.level == SecurityLevel.HIGH]
        medium = [f for f in self.findings if f.level == SecurityLevel.MEDIUM]
        low = [f for f in self.findings if f.level == SecurityLevel.LOW]
        
        print(f"\n📊 SECURITY FINDINGS SUMMARY:")
        print(f"   🔴 Critical: {len(critical)}")
        print(f"   🟠 High: {len(high)}")
        print(f"   🟡 Medium: {len(medium)}")
        print(f"   🟢 Low: {len(low)}")
        
        # Display findings
        for findings_list, title in [
            (critical, "CRITICAL SECURITY ISSUES"),
            (high, "HIGH PRIORITY ISSUES"),
            (medium, "MEDIUM PRIORITY ISSUES"),
            (low, "LOW PRIORITY ISSUES")
        ]:
            if findings_list:
                print(f"\n{title}:")
                print("-" * len(title))
                for i, finding in enumerate(findings_list, 1):
                    print(f"\n{finding.level.value} {i}. {finding.title}")
                    print(f"Description: {finding.description}")
                    print(f"Recommendation: {finding.recommendation}")
                    if finding.remediation_steps:
                        print("Remediation Steps:")
                        for step in finding.remediation_steps:
                            print(f"   {step}")

    def run_audit(self, json_output: bool = False):
        """Run the complete IAM security audit."""
        if not json_output:
            print("🚀 Starting AWS IAM Security Audit...")
            print(f"Current Identity: {self.current_arn}")
        
        # Analyze current user
        user_analysis = self.analyze_current_user(quiet=json_output)
        
        # Run security audits
        self.audit_root_user_usage(user_analysis)
        self.audit_user_permissions(user_analysis)
        self.audit_mfa_configuration(user_analysis)
        self.audit_access_keys(user_analysis)
        
        # Analyze all groups and users
        groups, users = self.analyze_groups_and_users(quiet=json_output)
        
        if json_output:
            # Generate and output JSON guide
            json_guide = self.generate_json_remediation_guide(user_analysis, groups, users)
            print(json.dumps(json_guide, indent=2, default=str))
        else:
            # Generate reports
            self.generate_security_report()
            self.recommend_non_root_setup(groups, users)
            
            # Final recommendations
            print(f"\n🎯 NEXT STEPS:")
            if any(f.level == SecurityLevel.CRITICAL for f in self.findings):
                print("   1. Address CRITICAL issues immediately")
                print("   2. Implement MFA on all privileged accounts")
                print("   3. Review and reduce excessive permissions")
            else:
                print("   1. Enable MFA if not already done")
                print("   2. Review user permissions regularly")
                print("   3. Rotate access keys every 90 days")
            
            print("\n📚 Additional Resources:")
            print("   • AWS IAM Best Practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html")
            print("   • Root User Best Practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html")
            print("   • IAM Access Analyzer: https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html")

    def run_audit(self, json_output: bool = False):
        """Run the complete IAM security audit."""
        if not json_output:
            print("🚀 Starting AWS IAM Security Audit...")
            print(f"Current Identity: {self.current_arn}")
        
        # Analyze current user
        user_analysis = self.analyze_current_user(quiet=json_output)
        
        # Run security audits
        self.audit_root_user_usage(user_analysis)
        self.audit_user_permissions(user_analysis)
        self.audit_mfa_configuration(user_analysis)
        self.audit_access_keys(user_analysis)
        
        # Analyze all groups and users
        groups, users = self.analyze_groups_and_users(quiet=json_output)
        
        if json_output:
            # Generate and output JSON guide
            json_guide = self.generate_json_remediation_guide(user_analysis, groups, users)
            print(json.dumps(json_guide, indent=2, default=str))
        else:
            # Generate reports
            self.generate_security_report()
            self.recommend_non_root_setup(groups, users)
            
            # Final recommendations
            print(f"\n🎯 NEXT STEPS:")
            if any(f.level == SecurityLevel.CRITICAL for f in self.findings):
                print("   1. Address CRITICAL issues immediately")
                print("   2. Implement MFA on all privileged accounts")
                print("   3. Review and reduce excessive permissions")
            else:
                print("   1. Enable MFA if not already done")
                print("   2. Review user permissions regularly")
                print("   3. Rotate access keys every 90 days")
            
            print("\n📚 Additional Resources:")
            print("   • AWS IAM Best Practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html")
            print("   • Root User Best Practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/root-user-best-practices.html")
            print("   • IAM Access Analyzer: https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html")

def main():
    """Main function to run the IAM security audit."""
    parser = argparse.ArgumentParser(
        description="AWS IAM Security Audit Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python a-iam-check.py                    # Run full audit
  python a-iam-check.py --current-user     # Analyze only current user
  python a-iam-check.py --recommendations  # Show setup recommendations only
  python a-iam-check.py --json-output      # Output detailed JSON remediation guide
  python a-iam-check.py --current-user --json-output  # JSON output for current user

The JSON output provides a structured remediation guide that can be consumed by
automation scripts to implement the recommended security changes.
        """
    )
    
    parser.add_argument(
        '--current-user', 
        action='store_true',
        help='Analyze only the current user (faster)'
    )
    
    parser.add_argument(
        '--recommendations', 
        action='store_true',
        help='Show setup recommendations only'
    )
    
    parser.add_argument(
        '--json-output', 
        action='store_true',
        help='Output detailed JSON remediation guide for automation scripts'
    )
    
    args = parser.parse_args()
    
    try:
        auditor = IAMSecurityAuditor()
        
        if args.recommendations:
            groups, users = auditor.analyze_groups_and_users()
            auditor.recommend_non_root_setup(groups, users)
        elif args.current_user:
            user_analysis = auditor.analyze_current_user(quiet=args.json_output)
            auditor.audit_root_user_usage(user_analysis)
            auditor.audit_user_permissions(user_analysis)
            auditor.audit_mfa_configuration(user_analysis)
            auditor.audit_access_keys(user_analysis)
            
            if args.json_output:
                groups, users = auditor.analyze_groups_and_users(quiet=True)
                json_guide = auditor.generate_json_remediation_guide(user_analysis, groups, users)
                print(json.dumps(json_guide, indent=2, default=str))
            else:
                auditor.generate_security_report()
        else:
            auditor.run_audit(json_output=args.json_output)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Audit interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Audit failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
