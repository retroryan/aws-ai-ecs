#!/usr/bin/env python3
"""
AWS IAM Security Checker - Comprehensive Edition

This script provides comprehensive IAM security analysis following AWS Well-Architected Framework
and Security Best Practices. It combines features from multiple tools to provide thorough
security assessment and actionable remediation guidance.

Features:
- Comprehensive security analysis with severity levels (CRITICAL, HIGH, MEDIUM, LOW, INFO)
- Root user detection and protection recommendations
- MFA status verification for all users
- Access key age analysis and rotation recommendations
- Policy analysis for overly permissive permissions
- Group-based permission management recommendations
- Password policy compliance checking
- Unused IAM resources detection
- Service control policy (SCP) awareness
- Detailed remediation steps with AWS CLI commands
- JSON output for automation with execution plans
- Security scoring system (0-100)
- Integration with auto-remediation tools

Usage:
    python iam-check.py                                      # Human-readable report
    python iam-check.py --json --format pretty --output findings.json  # Save pretty JSON 
    python iam-check.py --output report.txt                  # Save human-readable report to file
    python iam-check.py --severity high                      # Filter by minimum severity

AWS Well-Architected Framework Alignment:
- Security Pillar: Identity and Access Management
- Operational Excellence: Security automation
- Reliability: Least privilege access
"""

import boto3
import json
import sys
import argparse
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from botocore.exceptions import ClientError, NoCredentialsError


class Severity(Enum):
    """Security finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    
    @property
    def weight(self) -> int:
        """Return weight for scoring calculation."""
        weights = {
            Severity.CRITICAL: 40,
            Severity.HIGH: 20,
            Severity.MEDIUM: 10,
            Severity.LOW: 5,
            Severity.INFO: 0
        }
        return weights[self]
    
    def __ge__(self, other):
        """Compare severity levels."""
        if not isinstance(other, Severity):
            return NotImplemented
        order = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        return order.index(self) >= order.index(other)


@dataclass
class SecurityFinding:
    """Represents a security finding."""
    finding_id: str
    title: str
    description: str
    severity: Severity
    resource: str
    recommendation: str
    risk: str
    compliance: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "resource": self.resource,
            "recommendation": self.recommendation,
            "risk": self.risk,
            "compliance": self.compliance,
            "references": self.references
        }


@dataclass
class RemediationStep:
    """Represents a remediation step with execution details."""
    step_number: int
    description: str
    commands: List[str]
    prerequisites: List[str] = field(default_factory=list)
    validation: Optional[str] = None
    rollback: Optional[str] = None
    estimated_time: str = "< 1 minute"
    automation_safe: bool = True
    requires_human_review: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "step_number": self.step_number,
            "description": self.description,
            "commands": self.commands,
            "prerequisites": self.prerequisites,
            "validation": self.validation,
            "rollback": self.rollback,
            "estimated_time": self.estimated_time,
            "automation_safe": self.automation_safe,
            "requires_human_review": self.requires_human_review
        }


@dataclass
class Recommendation:
    """Represents a security recommendation with remediation steps."""
    recommendation_id: str
    title: str
    description: str
    severity: Severity
    category: str
    impact: str
    effort: str
    related_findings: List[str] = field(default_factory=list)
    remediation_steps: List[RemediationStep] = field(default_factory=list)
    alternative_approaches: List[str] = field(default_factory=list)
    prevention_tips: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "recommendation_id": self.recommendation_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category,
            "impact": self.impact,
            "effort": self.effort,
            "related_findings": self.related_findings,
            "remediation_steps": [step.to_dict() for step in self.remediation_steps],
            "alternative_approaches": self.alternative_approaches,
            "prevention_tips": self.prevention_tips
        }


class IAMSecurityChecker:
    """Comprehensive AWS IAM Security Checker."""
    
    def __init__(self):
        """Initialize AWS clients and configuration."""
        try:
            self.sts = boto3.client('sts')
            self.iam = boto3.client('iam')
            self.organizations = boto3.client('organizations')
            self.account_id = None
            self.caller_identity = None
            self.findings: List[SecurityFinding] = []
            self.recommendations: List[Recommendation] = []
            self.security_score = 100
            self.is_root_user = False
            self.current_user_name = None
            self.credential_report = None
        except NoCredentialsError:
            print("❌ Error: No AWS credentials found. Please configure AWS credentials.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error initializing AWS clients: {e}")
            sys.exit(1)
    
    def run_analysis(self, min_severity: Severity = Severity.INFO, current_user_only: bool = False, quiet: bool = False) -> Dict[str, Any]:
        """Run comprehensive IAM security analysis."""
        if not quiet:
            print("🔍 Starting comprehensive IAM security analysis...\n")
        
        # Get current identity
        self.get_current_identity()
        
        # Generate credential report
        self.generate_credential_report()
        
        # Run security checks
        self.check_root_user_usage()
        self.check_current_user_security()
        
        if not current_user_only:
            self.analyze_all_users()
            self.analyze_groups()
            self.analyze_policies()
            self.check_password_policy()
            self.check_unused_resources()
            self.check_cross_account_access()
            self.check_service_control_policies()
        
        # Generate recommendations based on findings
        self.generate_recommendations()
        
        # Calculate security score
        self.calculate_security_score()
        
        # Filter findings by severity
        filtered_findings = [f for f in self.findings if f.severity >= min_severity]
        
        return {
            "account_id": self.account_id,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "security_score": self.security_score,
            "total_findings": len(self.findings),
            "filtered_findings": len(filtered_findings),
            "findings_by_severity": self.get_findings_by_severity(),
            "findings": filtered_findings,
            "recommendations": self.recommendations,
            "executive_summary": self.generate_executive_summary(),
            "best_practices": self.get_best_practices()
        }
    
    def get_current_identity(self) -> Dict[str, Any]:
        """Get information about the current AWS caller identity."""
        try:
            self.caller_identity = self.sts.get_caller_identity()
            self.account_id = self.caller_identity['Account']
            
            # Determine if root user
            arn = self.caller_identity['Arn']
            self.is_root_user = ':root' in arn or arn.endswith(f':root')
            
            # Extract user/role name
            if 'assumed-role' in arn:
                self.current_user_name = arn.split('/')[-1]
            elif 'user' in arn:
                self.current_user_name = arn.split('/')[-1]
            else:
                self.current_user_name = 'Unknown'
            
            return self.caller_identity
        except ClientError as e:
            self.add_finding(
                SecurityFinding(
                    finding_id="IAM-001",
                    title="Unable to determine caller identity",
                    description=f"Failed to retrieve caller identity: {str(e)}",
                    severity=Severity.HIGH,
                    resource="Current credentials",
                    recommendation="Ensure AWS credentials are properly configured",
                    risk="Unable to perform security analysis without valid credentials",
                    compliance=["AWS-WAF-SEC01"]
                )
            )
            raise
    
    def generate_credential_report(self):
        """Generate and retrieve IAM credential report."""
        try:
            # Request credential report generation
            self.iam.generate_credential_report()
            
            # Wait for report to be ready (with timeout)
            import time
            max_attempts = 10
            for _ in range(max_attempts):
                response = self.iam.get_credential_report()
                if response.get('Content'):
                    import csv
                    import io
                    content = response['Content'].decode('utf-8')
                    self.credential_report = list(csv.DictReader(io.StringIO(content)))
                    return
                time.sleep(1)
            
            self.add_finding(
                SecurityFinding(
                    finding_id="IAM-002",
                    title="Credential report generation timeout",
                    description="Unable to generate IAM credential report within timeout period",
                    severity=Severity.MEDIUM,
                    resource="IAM Credential Report",
                    recommendation="Retry the analysis or check IAM permissions",
                    risk="Limited visibility into user credential status",
                    compliance=["AWS-WAF-SEC02"]
                )
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'AccessDenied':
                self.add_finding(
                    SecurityFinding(
                        finding_id="IAM-003",
                        title="Insufficient permissions for credential report",
                        description="Current user lacks permissions to generate credential report",
                        severity=Severity.MEDIUM,
                        resource="IAM Permissions",
                        recommendation="Grant iam:GenerateCredentialReport and iam:GetCredentialReport permissions",
                        risk="Unable to analyze user credentials comprehensively",
                        compliance=["AWS-WAF-SEC02"]
                    )
                )
    
    def check_root_user_usage(self):
        """Check if root user is being used."""
        if self.is_root_user:
            self.add_finding(
                SecurityFinding(
                    finding_id="IAM-004",
                    title="Root user detected",
                    description="You are currently using root user credentials",
                    severity=Severity.CRITICAL,
                    resource=f"Account {self.account_id} root user",
                    recommendation="Stop using root user immediately and switch to an IAM user or role",
                    risk="Root user has unrestricted access to all resources and actions",
                    compliance=["AWS-WAF-SEC03", "CIS-AWS-1.1"],
                    references=[
                        "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#lock-away-credentials"
                    ]
                )
            )
    
    def check_current_user_security(self):
        """Analyze security of current user/role."""
        if self.is_root_user:
            return  # Root user checks handled separately
        
        # Check if using temporary credentials (recommended)
        if 'SessionToken' in self.caller_identity:
            self.add_finding(
                SecurityFinding(
                    finding_id="IAM-005",
                    title="Using temporary credentials",
                    description="Current session is using temporary credentials",
                    severity=Severity.INFO,
                    resource=self.caller_identity['Arn'],
                    recommendation="Continue using temporary credentials when possible",
                    risk="None - This is a security best practice",
                    compliance=["AWS-WAF-SEC04"]
                )
            )
        
        # Check MFA for current user if it's an IAM user
        if 'user/' in self.caller_identity.get('Arn', ''):
            self.check_user_mfa(self.current_user_name)
    
    def analyze_all_users(self):
        """Analyze all IAM users for security issues."""
        try:
            paginator = self.iam.get_paginator('list_users')
            
            for page in paginator.paginate():
                for user in page['Users']:
                    self.analyze_user(user)
            
        except ClientError as e:
            self.add_finding(
                SecurityFinding(
                    finding_id="IAM-006",
                    title="Unable to list IAM users",
                    description=f"Failed to retrieve IAM users: {str(e)}",
                    severity=Severity.HIGH,
                    resource="IAM Users",
                    recommendation="Ensure iam:ListUsers permission is granted",
                    risk="Unable to analyze user security comprehensively",
                    compliance=["AWS-WAF-SEC02"]
                )
            )
    
    def analyze_user(self, user: Dict[str, Any]):
        """Analyze individual IAM user for security issues."""
        user_name = user['UserName']
        
        # Check for old access keys
        try:
            access_keys = self.iam.list_access_keys(UserName=user_name)
            for key in access_keys['AccessKeyMetadata']:
                if key['Status'] == 'Active':
                    age = datetime.now(timezone.utc) - key['CreateDate']
                    if age > timedelta(days=90):
                        self.add_finding(
                            SecurityFinding(
                                finding_id=f"IAM-KEY-{user_name}-{key['AccessKeyId'][-4:]}",
                                title=f"Old access key for user {user_name}",
                                description=f"Access key {key['AccessKeyId']} is {age.days} days old",
                                severity=Severity.HIGH,
                                resource=f"User: {user_name}, Key: {key['AccessKeyId']}",
                                recommendation="Rotate access key - keys should be rotated every 90 days",
                                risk="Old access keys increase risk of compromise",
                                compliance=["AWS-WAF-SEC05", "CIS-AWS-1.4"],
                                references=[
                                    "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#rotate-credentials"
                                ]
                            )
                        )
                    
                    # Check for unused access keys
                    if self.credential_report:
                        for cred in self.credential_report:
                            if cred.get('user') == user_name and cred.get(f'access_key_{key["AccessKeyId"][-1]}_last_used_date') == 'N/A':
                                self.add_finding(
                                    SecurityFinding(
                                        finding_id=f"IAM-UNUSED-KEY-{user_name}-{key['AccessKeyId'][-4:]}",
                                        title=f"Unused access key for user {user_name}",
                                        description=f"Access key {key['AccessKeyId']} has never been used",
                                        severity=Severity.MEDIUM,
                                        resource=f"User: {user_name}, Key: {key['AccessKeyId']}",
                                        recommendation="Remove unused access keys",
                                        risk="Unused credentials increase attack surface",
                                        compliance=["AWS-WAF-SEC06"]
                                    )
                                )
        except ClientError:
            pass
        
        # Check MFA status
        self.check_user_mfa(user_name)
        
        # Check for inline policies (less preferred than managed policies)
        try:
            inline_policies = self.iam.list_user_policies(UserName=user_name)
            if inline_policies['PolicyNames']:
                self.add_finding(
                    SecurityFinding(
                        finding_id=f"IAM-INLINE-{user_name}",
                        title=f"Inline policies found for user {user_name}",
                        description=f"User has {len(inline_policies['PolicyNames'])} inline policies",
                        severity=Severity.LOW,
                        resource=f"User: {user_name}",
                        recommendation="Consider using managed policies instead of inline policies",
                        risk="Inline policies are harder to manage and audit",
                        compliance=["AWS-WAF-SEC07"]
                    )
                )
        except ClientError:
            pass
    
    def check_user_mfa(self, user_name: str):
        """Check if user has MFA enabled."""
        try:
            mfa_devices = self.iam.list_mfa_devices(UserName=user_name)
            if not mfa_devices['MFADevices']:
                self.add_finding(
                    SecurityFinding(
                        finding_id=f"IAM-MFA-{user_name}",
                        title=f"MFA not enabled for user {user_name}",
                        description="Multi-factor authentication is not configured",
                        severity=Severity.HIGH,
                        resource=f"User: {user_name}",
                        recommendation="Enable MFA for all IAM users",
                        risk="Account vulnerable to password compromise",
                        compliance=["AWS-WAF-SEC08", "CIS-AWS-1.2"],
                        references=[
                            "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html"
                        ]
                    )
                )
        except ClientError:
            pass
    
    def analyze_groups(self):
        """Analyze IAM groups for security best practices."""
        try:
            groups = self.iam.list_groups()
            
            if not groups['Groups']:
                self.add_finding(
                    SecurityFinding(
                        finding_id="IAM-GROUPS-001",
                        title="No IAM groups configured",
                        description="No IAM groups found in the account",
                        severity=Severity.MEDIUM,
                        resource="IAM Groups",
                        recommendation="Create groups to manage permissions efficiently",
                        risk="Managing permissions per user is error-prone and hard to audit",
                        compliance=["AWS-WAF-SEC09"]
                    )
                )
            else:
                # Check for groups without users
                for group in groups['Groups']:
                    group_name = group['GroupName']
                    try:
                        group_users = self.iam.get_group(GroupName=group_name)
                        if not group_users['Users']:
                            self.add_finding(
                                SecurityFinding(
                                    finding_id=f"IAM-EMPTY-GROUP-{group_name}",
                                    title=f"Empty group: {group_name}",
                                    description="Group has no members",
                                    severity=Severity.LOW,
                                    resource=f"Group: {group_name}",
                                    recommendation="Remove unused groups or add appropriate users",
                                    risk="Unused resources complicate security audits",
                                    compliance=["AWS-WAF-SEC10"]
                                )
                            )
                    except ClientError:
                        pass
        except ClientError as e:
            self.add_finding(
                SecurityFinding(
                    finding_id="IAM-GROUPS-002",
                    title="Unable to analyze groups",
                    description=f"Failed to list groups: {str(e)}",
                    severity=Severity.MEDIUM,
                    resource="IAM Groups",
                    recommendation="Ensure iam:ListGroups permission is granted",
                    risk="Unable to analyze group-based permissions",
                    compliance=["AWS-WAF-SEC02"]
                )
            )
    
    def analyze_policies(self):
        """Analyze IAM policies for security issues."""
        try:
            # Check for policies with wildcard permissions
            policies = self.iam.list_policies(Scope='Local')
            
            for policy in policies['Policies']:
                if policy['AttachmentCount'] > 0:
                    try:
                        policy_version = self.iam.get_policy_version(
                            PolicyArn=policy['Arn'],
                            VersionId=policy['DefaultVersionId']
                        )
                        
                        policy_doc = policy_version['PolicyVersion']['Document']
                        self.analyze_policy_document(policy['PolicyName'], policy_doc)
                    except ClientError:
                        pass
        except ClientError:
            pass
    
    def analyze_policy_document(self, policy_name: str, policy_doc: Dict[str, Any]):
        """Analyze policy document for security issues."""
        for statement in policy_doc.get('Statement', []):
            if statement.get('Effect') == 'Allow':
                actions = statement.get('Action', [])
                if isinstance(actions, str):
                    actions = [actions]
                
                resources = statement.get('Resource', [])
                if isinstance(resources, str):
                    resources = [resources]
                
                # Check for overly permissive actions
                for action in actions:
                    if action == '*' or action == '*:*':
                        self.add_finding(
                            SecurityFinding(
                                finding_id=f"IAM-POLICY-WILDCARD-{policy_name}",
                                title=f"Wildcard actions in policy {policy_name}",
                                description="Policy allows all actions (*)",
                                severity=Severity.HIGH,
                                resource=f"Policy: {policy_name}",
                                recommendation="Follow least privilege principle - specify exact actions needed",
                                risk="Overly permissive policies violate least privilege",
                                compliance=["AWS-WAF-SEC11", "CIS-AWS-1.22"]
                            )
                        )
                
                # Check for overly permissive resources
                for resource in resources:
                    if resource == '*':
                        self.add_finding(
                            SecurityFinding(
                                finding_id=f"IAM-POLICY-RESOURCE-{policy_name}",
                                title=f"Wildcard resources in policy {policy_name}",
                                description="Policy applies to all resources (*)",
                                severity=Severity.MEDIUM,
                                resource=f"Policy: {policy_name}",
                                recommendation="Specify exact resources when possible",
                                risk="Broad resource access increases blast radius",
                                compliance=["AWS-WAF-SEC12"]
                            )
                        )
    
    def check_password_policy(self):
        """Check account password policy compliance."""
        try:
            password_policy = self.iam.get_account_password_policy()
            policy = password_policy['PasswordPolicy']
            
            # Check against CIS benchmarks
            issues = []
            
            if policy.get('MinimumPasswordLength', 0) < 14:
                issues.append("Minimum password length should be at least 14 characters")
            
            if not policy.get('RequireUppercaseCharacters', False):
                issues.append("Should require uppercase characters")
            
            if not policy.get('RequireLowercaseCharacters', False):
                issues.append("Should require lowercase characters")
            
            if not policy.get('RequireNumbers', False):
                issues.append("Should require numbers")
            
            if not policy.get('RequireSymbols', False):
                issues.append("Should require symbols")
            
            if policy.get('MaxPasswordAge', 0) == 0 or policy.get('MaxPasswordAge', 91) > 90:
                issues.append("Password expiration should be set to 90 days or less")
            
            if policy.get('PasswordReusePrevention', 0) < 24:
                issues.append("Should prevent reuse of last 24 passwords")
            
            if issues:
                self.add_finding(
                    SecurityFinding(
                        finding_id="IAM-PASSWORD-POLICY",
                        title="Password policy does not meet security standards",
                        description=f"Issues found: {'; '.join(issues)}",
                        severity=Severity.MEDIUM,
                        resource="Account Password Policy",
                        recommendation="Update password policy to meet CIS benchmarks",
                        risk="Weak password policies increase risk of account compromise",
                        compliance=["CIS-AWS-1.5-1.11"],
                        references=[
                            "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_passwords_account-policy.html"
                        ]
                    )
                )
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                self.add_finding(
                    SecurityFinding(
                        finding_id="IAM-NO-PASSWORD-POLICY",
                        title="No password policy configured",
                        description="Account has no password policy set",
                        severity=Severity.HIGH,
                        resource="Account Password Policy",
                        recommendation="Configure a strong password policy",
                        risk="Default password requirements are insufficient",
                        compliance=["CIS-AWS-1.5-1.11"]
                    )
                )
    
    def check_unused_resources(self):
        """Check for unused IAM resources."""
        # Check for unused roles
        try:
            roles = self.iam.list_roles()
            for role in roles['Roles']:
                role_name = role['RoleName']
                
                # Skip AWS service-linked roles
                if role.get('Path', '').startswith('/aws-service-role/'):
                    continue
                
                try:
                    # Check last used
                    role_details = self.iam.get_role(RoleName=role_name)
                    last_used = role_details['Role'].get('RoleLastUsed')
                    
                    if not last_used:
                        self.add_finding(
                            SecurityFinding(
                                finding_id=f"IAM-UNUSED-ROLE-{role_name}",
                                title=f"Unused role: {role_name}",
                                description="Role has never been used",
                                severity=Severity.LOW,
                                resource=f"Role: {role_name}",
                                recommendation="Remove unused roles to reduce attack surface",
                                risk="Unused roles can be compromised and go unnoticed",
                                compliance=["AWS-WAF-SEC13"]
                            )
                        )
                    else:
                        last_used_date = last_used.get('LastUsedDate')
                        if last_used_date:
                            age = datetime.now(timezone.utc) - last_used_date
                            if age > timedelta(days=90):
                                self.add_finding(
                                    SecurityFinding(
                                        finding_id=f"IAM-STALE-ROLE-{role_name}",
                                        title=f"Stale role: {role_name}",
                                        description=f"Role not used for {age.days} days",
                                        severity=Severity.LOW,
                                        resource=f"Role: {role_name}",
                                        recommendation="Review and possibly remove stale roles",
                                        risk="Stale roles may have outdated permissions",
                                        compliance=["AWS-WAF-SEC13"]
                                    )
                                )
                except ClientError:
                    pass
        except ClientError:
            pass
    
    def check_cross_account_access(self):
        """Check for cross-account access configurations."""
        try:
            roles = self.iam.list_roles()
            
            for role in roles['Roles']:
                assume_role_doc = role['AssumeRolePolicyDocument']
                
                for statement in assume_role_doc.get('Statement', []):
                    if statement.get('Effect') == 'Allow':
                        principal = statement.get('Principal', {})
                        
                        # Check for external account access
                        if isinstance(principal, dict) and 'AWS' in principal:
                            aws_principals = principal['AWS']
                            if isinstance(aws_principals, str):
                                aws_principals = [aws_principals]
                            
                            for arn in aws_principals:
                                if ':root' in arn and self.account_id not in arn:
                                    external_account = arn.split(':')[4]
                                    self.add_finding(
                                        SecurityFinding(
                                            finding_id=f"IAM-CROSS-ACCOUNT-{role['RoleName']}",
                                            title=f"Cross-account access in role {role['RoleName']}",
                                            description=f"Role can be assumed by external account {external_account}",
                                            severity=Severity.MEDIUM,
                                            resource=f"Role: {role['RoleName']}",
                                            recommendation="Review and document all cross-account access",
                                            risk="Unintended cross-account access can lead to data exposure",
                                            compliance=["AWS-WAF-SEC14"]
                                        )
                                    )
        except ClientError:
            pass
    
    def check_service_control_policies(self):
        """Check if Service Control Policies are in use."""
        try:
            # Check if account is part of an organization
            org_info = self.organizations.describe_organization()
            
            # Check for SCPs
            try:
                policies = self.organizations.list_policies(Filter='SERVICE_CONTROL_POLICY')
                if not policies['Policies']:
                    self.add_finding(
                        SecurityFinding(
                            finding_id="IAM-NO-SCPS",
                            title="No Service Control Policies configured",
                            description="Organization has no SCPs for permissions guardrails",
                            severity=Severity.MEDIUM,
                            resource="AWS Organization",
                            recommendation="Implement SCPs for defense in depth",
                            risk="Missing preventive controls at organization level",
                            compliance=["AWS-WAF-SEC15"],
                            references=[
                                "https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html"
                            ]
                        )
                    )
            except ClientError:
                pass
        except ClientError:
            # Not part of an organization or no access
            pass
    
    def add_finding(self, finding: SecurityFinding):
        """Add a security finding to the results."""
        self.findings.append(finding)
    
    def get_findings_by_severity(self) -> Dict[str, int]:
        """Get count of findings by severity level."""
        counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        for finding in self.findings:
            counts[finding.severity.value] += 1
        
        return counts
    
    def calculate_security_score(self):
        """Calculate overall security score based on findings."""
        score = 100
        
        for finding in self.findings:
            score -= finding.severity.weight
        
        self.security_score = max(0, score)
    
    def generate_executive_summary(self) -> str:
        """Generate executive summary of findings."""
        severity_counts = self.get_findings_by_severity()
        
        if severity_counts['critical'] > 0:
            risk_level = "CRITICAL"
            action = "Immediate action required"
        elif severity_counts['high'] > 0:
            risk_level = "HIGH"
            action = "Urgent remediation needed"
        elif severity_counts['medium'] > 0:
            risk_level = "MEDIUM"
            action = "Plan remediation activities"
        elif severity_counts['low'] > 0:
            risk_level = "LOW"
            action = "Review and improve"
        else:
            risk_level = "MINIMAL"
            action = "Maintain current security posture"
        
        summary = f"""IAM Security Assessment Summary
Account: {self.account_id}
Risk Level: {risk_level}
Security Score: {self.security_score}/100
Action Required: {action}

Findings Summary:
- Critical: {severity_counts['critical']}
- High: {severity_counts['high']}
- Medium: {severity_counts['medium']}
- Low: {severity_counts['low']}
- Info: {severity_counts['info']}

Top Risks Identified:"""
        
        # Add top 3 critical/high findings
        critical_high = [f for f in self.findings if f.severity in [Severity.CRITICAL, Severity.HIGH]]
        for finding in critical_high[:3]:
            summary += f"\n- {finding.title}"
        
        return summary
    
    def get_best_practices(self) -> Dict[str, List[str]]:
        """Get IAM best practices organized by category."""
        return {
            "root_user": [
                "Never use root user for daily tasks",
                "Enable MFA on root user account",
                "Delete all root user access keys",
                "Store root credentials in secure vault",
                "Document root password recovery process",
                "Only use root for account-level changes"
            ],
            "iam_users": [
                "Enable MFA on all IAM users",
                "Use groups for permission management",
                "Apply least privilege principle",
                "Rotate access keys every 90 days",
                "Remove unused access keys",
                "Use strong password policy",
                "Regular access reviews (quarterly)"
            ],
            "groups": [
                "Use groups instead of direct policy attachment",
                "Create role-based groups (Admin, Developer, ReadOnly)",
                "Regularly audit group memberships",
                "Document group purposes",
                "Avoid nested group memberships"
            ],
            "policies": [
                "Avoid wildcard (*) permissions",
                "Use AWS managed policies when possible",
                "Version custom policies",
                "Use policy conditions for additional security",
                "Regular policy reviews",
                "Use IAM Access Analyzer"
            ],
            "access_keys": [
                "Rotate keys every 90 days maximum",
                "Use temporary credentials when possible",
                "Never embed keys in code",
                "Use IAM roles for EC2/Lambda",
                "Monitor key usage with CloudTrail",
                "Delete unused keys immediately"
            ],
            "general": [
                "Enable CloudTrail for audit logging",
                "Use AWS Organizations for multi-account",
                "Implement SCPs for guardrails",
                "Use IAM Access Analyzer",
                "Regular security assessments",
                "Automate compliance checks"
            ]
        }
    
    def generate_recommendations(self):
        """Generate actionable recommendations based on findings."""
        # Group findings by category
        categories = {}
        for finding in self.findings:
            if finding.severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM]:
                category = self.categorize_finding(finding)
                if category not in categories:
                    categories[category] = []
                categories[category].append(finding)
        
        # Generate recommendations for each category
        if 'root_user' in categories:
            self.generate_root_user_recommendations()
        
        if 'mfa' in categories:
            self.generate_mfa_recommendations()
        
        if 'access_keys' in categories:
            self.generate_access_key_recommendations()
        
        if 'policies' in categories:
            self.generate_policy_recommendations()
        
        if 'unused_resources' in categories:
            self.generate_cleanup_recommendations()
        
        # Generate group-based recommendations
        self.generate_group_based_recommendations()
    
    def categorize_finding(self, finding: SecurityFinding) -> str:
        """Categorize finding for recommendation grouping."""
        finding_id = finding.finding_id.upper()
        
        if 'ROOT' in finding_id:
            return 'root_user'
        elif 'MFA' in finding_id:
            return 'mfa'
        elif 'KEY' in finding_id:
            return 'access_keys'
        elif 'POLICY' in finding_id or 'WILDCARD' in finding_id:
            return 'policies'
        elif 'UNUSED' in finding_id or 'STALE' in finding_id or 'EMPTY' in finding_id:
            return 'unused_resources'
        else:
            return 'other'
    
    def generate_root_user_recommendations(self):
        """Generate recommendations for root user issues."""
        recommendation = Recommendation(
            recommendation_id="REC-ROOT-001",
            title="Secure Root User Account",
            description="Implement comprehensive root user security measures",
            severity=Severity.CRITICAL,
            category="Identity Security",
            impact="Prevents unauthorized access to highest privilege account",
            effort="Medium",
            related_findings=["IAM-004"],
            remediation_steps=[
                RemediationStep(
                    step_number=1,
                    description="Enable MFA on root user",
                    commands=[
                        "# Log in to AWS Console as root user",
                        "# Navigate to Security Credentials",
                        "# Set up virtual or hardware MFA device"
                    ],
                    prerequisites=["Access to root user email", "MFA device or app"],
                    validation="aws iam get-account-summary --query 'SummaryMap.AccountMFAEnabled'",
                    estimated_time="10 minutes",
                    automation_safe=False,
                    requires_human_review=True
                ),
                RemediationStep(
                    step_number=2,
                    description="Create administrative IAM user",
                    commands=[
                        "aws iam create-user --user-name admin-user",
                        "aws iam attach-user-policy --user-name admin-user --policy-arn arn:aws:iam::aws:policy/AdministratorAccess",
                        "aws iam create-access-key --user-name admin-user"
                    ],
                    prerequisites=["IAM permissions", "Secure password storage"],
                    validation="aws iam get-user --user-name admin-user",
                    rollback="aws iam delete-user --user-name admin-user",
                    estimated_time="5 minutes"
                ),
                RemediationStep(
                    step_number=3,
                    description="Delete root user access keys",
                    commands=[
                        "# Log in to AWS Console as root user",
                        "# Navigate to Security Credentials",
                        "# Delete any existing access keys"
                    ],
                    prerequisites=["Ensure no processes use root access keys"],
                    validation="# Check in AWS Console Security Credentials",
                    estimated_time="5 minutes",
                    automation_safe=False,
                    requires_human_review=True
                ),
                RemediationStep(
                    step_number=4,
                    description="Set up root user activity monitoring",
                    commands=[
                        "# Create CloudWatch alarm for root user activity",
                        "aws cloudwatch put-metric-alarm --alarm-name RootUserActivity --alarm-description 'Alert on root user login' --metric-name UserLoginEvents --namespace CloudTrailMetrics --statistic Sum --period 300 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --evaluation-periods 1"
                    ],
                    prerequisites=["CloudTrail enabled", "SNS topic for alerts"],
                    validation="aws cloudwatch describe-alarms --alarm-names RootUserActivity",
                    estimated_time="15 minutes"
                )
            ],
            alternative_approaches=[
                "Use AWS Organizations to apply SCPs that restrict root user actions",
                "Implement break-glass procedures for emergency root access"
            ],
            prevention_tips=[
                "Store root credentials in a secure vault",
                "Require multiple approvals for root access",
                "Regular audit of root user activity"
            ]
        )
        self.recommendations.append(recommendation)
    
    def generate_mfa_recommendations(self):
        """Generate recommendations for MFA issues."""
        mfa_findings = [f for f in self.findings if 'MFA' in f.finding_id]
        affected_users = [f.resource.split(': ')[1] for f in mfa_findings if f.severity >= Severity.HIGH]
        
        recommendation = Recommendation(
            recommendation_id="REC-MFA-001",
            title="Enable Multi-Factor Authentication",
            description="Enable MFA for all IAM users to add an extra layer of security",
            severity=Severity.HIGH,
            category="Authentication Security",
            impact="Significantly reduces risk of account compromise",
            effort="Low",
            related_findings=[f.finding_id for f in mfa_findings],
            remediation_steps=[
                RemediationStep(
                    step_number=1,
                    description="Enable MFA for each user",
                    commands=[
                        f"# For user: {user}" for user in affected_users[:3]
                    ] + [
                        "# Users must:",
                        "# 1. Sign in to AWS Console",
                        "# 2. Go to Security Credentials",
                        "# 3. Set up Virtual MFA device"
                    ],
                    prerequisites=["Users have AWS Console access", "MFA app installed"],
                    validation="aws iam list-mfa-devices --user-name <username>",
                    estimated_time="5 minutes per user",
                    automation_safe=False,
                    requires_human_review=True
                ),
                RemediationStep(
                    step_number=2,
                    description="Create IAM policy requiring MFA",
                    commands=[
                        """aws iam create-policy --policy-name RequireMFAPolicy --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "Bool": {
          "aws:MultiFactorAuthPresent": "false"
        }
      }
    }
  ]
}'"""
                    ],
                    prerequisites=["IAM policy creation permissions"],
                    validation="aws iam get-policy --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/RequireMFAPolicy",
                    estimated_time="5 minutes"
                )
            ],
            alternative_approaches=[
                "Use AWS SSO with enforced MFA at the identity provider level",
                "Implement conditional access policies based on risk"
            ],
            prevention_tips=[
                "Make MFA mandatory for all new users",
                "Regular MFA compliance audits",
                "Provide MFA setup documentation and training"
            ]
        )
        self.recommendations.append(recommendation)
    
    def generate_access_key_recommendations(self):
        """Generate recommendations for access key issues."""
        key_findings = [f for f in self.findings if 'KEY' in f.finding_id]
        
        recommendation = Recommendation(
            recommendation_id="REC-KEYS-001",
            title="Implement Access Key Rotation Policy",
            description="Establish and enforce regular access key rotation",
            severity=Severity.HIGH,
            category="Credential Management",
            impact="Reduces risk from compromised credentials",
            effort="Medium",
            related_findings=[f.finding_id for f in key_findings],
            remediation_steps=[
                RemediationStep(
                    step_number=1,
                    description="Identify and rotate old access keys",
                    commands=[
                        "# List all access keys older than 90 days",
                        """aws iam list-users --query 'Users[*].UserName' --output text | while read user; do
  echo "Checking $user:"
  aws iam list-access-keys --user-name $user --query 'AccessKeyMetadata[?CreateDate<=`'$(date -u -d '90 days ago' +%Y-%m-%d)'`]'
done"""
                    ],
                    prerequisites=["List of affected users", "Communication plan"],
                    validation="# Re-run the above command to verify",
                    estimated_time="30 minutes"
                ),
                RemediationStep(
                    step_number=2,
                    description="Create new access key for each user",
                    commands=[
                        "aws iam create-access-key --user-name <username>",
                        "# Securely share new credentials with user",
                        "# Update applications with new credentials"
                    ],
                    prerequisites=["Secure credential distribution method"],
                    validation="aws iam list-access-keys --user-name <username>",
                    estimated_time="10 minutes per user"
                ),
                RemediationStep(
                    step_number=3,
                    description="Delete old access keys after verification",
                    commands=[
                        "# After confirming new keys work:",
                        "aws iam delete-access-key --user-name <username> --access-key-id <old-key-id>"
                    ],
                    prerequisites=["Confirmation that new keys are working"],
                    validation="aws iam list-access-keys --user-name <username>",
                    rollback="# If issues occur, reactivate old key: aws iam update-access-key --user-name <username> --access-key-id <old-key-id> --status Active",
                    estimated_time="5 minutes per user"
                ),
                RemediationStep(
                    step_number=4,
                    description="Implement automated key rotation",
                    commands=[
                        "# Consider using AWS Secrets Manager for automatic rotation",
                        "# Or implement Lambda function for key rotation notifications"
                    ],
                    prerequisites=["AWS Lambda or Secrets Manager access"],
                    estimated_time="2 hours",
                    automation_safe=True
                )
            ],
            alternative_approaches=[
                "Use temporary credentials with IAM roles instead of long-term keys",
                "Implement IAM Roles Anywhere for external workloads"
            ],
            prevention_tips=[
                "Set up CloudWatch alarms for old access keys",
                "Use AWS Config rules to monitor key age",
                "Prefer temporary credentials over permanent keys"
            ]
        )
        self.recommendations.append(recommendation)
    
    def generate_policy_recommendations(self):
        """Generate recommendations for policy issues."""
        policy_findings = [f for f in self.findings if 'POLICY' in f.finding_id or 'WILDCARD' in f.finding_id]
        
        recommendation = Recommendation(
            recommendation_id="REC-POLICY-001",
            title="Implement Least Privilege Access",
            description="Review and restrict overly permissive IAM policies",
            severity=Severity.HIGH,
            category="Access Control",
            impact="Reduces blast radius of compromised credentials",
            effort="High",
            related_findings=[f.finding_id for f in policy_findings],
            remediation_steps=[
                RemediationStep(
                    step_number=1,
                    description="Analyze current permissions usage",
                    commands=[
                        "# Use IAM Access Analyzer to review permissions",
                        "aws accessanalyzer create-analyzer --analyzer-name iam-least-privilege --type ACCOUNT",
                        "# Generate policy based on actual usage",
                        "aws accessanalyzer start-policy-generation --policy-generation-details file://policy-gen-details.json"
                    ],
                    prerequisites=["IAM Access Analyzer enabled"],
                    validation="aws accessanalyzer list-analyzers",
                    estimated_time="1 hour"
                ),
                RemediationStep(
                    step_number=2,
                    description="Replace wildcard policies",
                    commands=[
                        "# Create specific policy replacing wildcards",
                        """aws iam create-policy --policy-name SpecificPolicy --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/*"
    }
  ]
}'"""
                    ],
                    prerequisites=["List of required permissions"],
                    validation="aws iam get-policy --policy-arn <new-policy-arn>",
                    estimated_time="30 minutes per policy"
                ),
                RemediationStep(
                    step_number=3,
                    description="Test with restricted permissions",
                    commands=[
                        "# Attach new policy to test user/role",
                        "aws iam attach-user-policy --user-name test-user --policy-arn <new-policy-arn>",
                        "# Test all required functionality",
                        "# Monitor CloudTrail for access denied errors"
                    ],
                    prerequisites=["Test environment", "Test scenarios"],
                    validation="# Run application test suite",
                    rollback="aws iam detach-user-policy --user-name test-user --policy-arn <new-policy-arn>",
                    estimated_time="2 hours"
                )
            ],
            alternative_approaches=[
                "Use AWS managed policies as a starting point",
                "Implement permission boundaries for delegated administration",
                "Use SCPs for organization-wide guardrails"
            ],
            prevention_tips=[
                "Review policies before deployment",
                "Use policy simulator to test permissions",
                "Implement policy validation in CI/CD pipeline"
            ]
        )
        self.recommendations.append(recommendation)
    
    def generate_cleanup_recommendations(self):
        """Generate recommendations for unused resources."""
        unused_findings = [f for f in self.findings if any(x in f.finding_id for x in ['UNUSED', 'STALE', 'EMPTY'])]
        
        recommendation = Recommendation(
            recommendation_id="REC-CLEANUP-001",
            title="Remove Unused IAM Resources",
            description="Clean up unused users, roles, groups, and policies",
            severity=Severity.LOW,
            category="Resource Hygiene",
            impact="Reduces attack surface and improves manageability",
            effort="Low",
            related_findings=[f.finding_id for f in unused_findings],
            remediation_steps=[
                RemediationStep(
                    step_number=1,
                    description="Generate usage report",
                    commands=[
                        "# Generate credential report",
                        "aws iam generate-credential-report",
                        "aws iam get-credential-report --query 'Content' --output text | base64 -d > credential-report.csv",
                        "# Review last used dates"
                    ],
                    prerequisites=["IAM read permissions"],
                    validation="test -f credential-report.csv",
                    estimated_time="10 minutes"
                ),
                RemediationStep(
                    step_number=2,
                    description="Remove unused access keys",
                    commands=[
                        "# For each unused key identified:",
                        "aws iam delete-access-key --user-name <username> --access-key-id <key-id>"
                    ],
                    prerequisites=["Confirmation keys are not needed"],
                    validation="aws iam list-access-keys --user-name <username>",
                    estimated_time="5 minutes per key"
                ),
                RemediationStep(
                    step_number=3,
                    description="Delete unused roles",
                    commands=[
                        "# First, detach all policies",
                        "aws iam list-attached-role-policies --role-name <role-name> --query 'AttachedPolicies[*].PolicyArn' --output text | xargs -I {} aws iam detach-role-policy --role-name <role-name> --policy-arn {}",
                        "# Then delete the role",
                        "aws iam delete-role --role-name <role-name>"
                    ],
                    prerequisites=["Verify role is truly unused"],
                    validation="aws iam get-role --role-name <role-name> 2>&1 | grep NoSuchEntity",
                    estimated_time="10 minutes per role"
                )
            ],
            alternative_approaches=[
                "Implement automated cleanup with Lambda",
                "Use AWS Config rules for continuous monitoring"
            ],
            prevention_tips=[
                "Tag resources with owner and purpose",
                "Regular access reviews (quarterly)",
                "Automated alerts for unused resources"
            ]
        )
        self.recommendations.append(recommendation)
    
    def generate_group_based_recommendations(self):
        """Generate recommendations for group-based permission management."""
        try:
            # Get all groups
            groups = []
            paginator = self.iam.get_paginator('list_groups')
            for page in paginator.paginate():
                for group in page['Groups']:
                    group_name = group['GroupName']
                    
                    # Get attached policies
                    attached_policies = self.iam.list_attached_group_policies(GroupName=group_name)
                    group_info = {
                        'name': group_name,
                        'attached_policies': [p['PolicyName'] for p in attached_policies['AttachedPolicies']],
                        'is_admin': False
                    }
                    
                    # Check if admin group
                    admin_indicators = ['AdministratorAccess', 'PowerUserAccess', 'admin', 'Admin']
                    for policy in group_info['attached_policies']:
                        if any(indicator in policy for indicator in admin_indicators):
                            group_info['is_admin'] = True
                            break
                    
                    groups.append(group_info)
            
            # Find admin groups
            admin_groups = [g for g in groups if g['is_admin']]
            
            # Generate recommendations based on findings
            if self.is_root_user and not admin_groups:
                self.recommendations.append(Recommendation(
                    recommendation_id="REC-GROUP-001",
                    title="Create Administrative Group",
                    description="No administrative groups found. Create an admin group for better permission management",
                    severity=Severity.HIGH,
                    category="Group Management",
                    impact="Improves permission management and reduces direct policy attachments",
                    effort="Low",
                    related_findings=["IAM-004"],
                    remediation_steps=[
                        RemediationStep(
                            step_number=1,
                            description="Create an administrative group and add admin user",
                            commands=[],
                            prerequisites=["IAM permissions to create groups"],
                            estimated_time="5 minutes"
                        )
                    ],
                    prevention_tips=[
                        "Always use groups for permission management",
                        "Avoid attaching policies directly to users",
                        "Create role-based groups (Admin, Developer, ReadOnly)"
                    ]
                ))
            elif self.is_root_user and admin_groups:
                best_admin_group = admin_groups[0]
                self.recommendations.append(Recommendation(
                    recommendation_id="REC-GROUP-002",
                    title="Use Existing Administrative Group",
                    description=f"Administrative group '{best_admin_group['name']}' exists. Add new admin user to this group",
                    severity=Severity.HIGH,
                    category="Group Management",
                    impact="Leverages existing group structure for consistent permissions",
                    effort="Low",
                    related_findings=["IAM-004"],
                    remediation_steps=[
                        RemediationStep(
                            step_number=1,
                            description=f"Add administrative user to group '{best_admin_group['name']}'",
                            commands=[],
                            prerequisites=["IAM permissions to modify group membership"],
                            estimated_time="2 minutes"
                        )
                    ],
                    prevention_tips=[
                        "Regularly review group memberships",
                        "Audit group permissions periodically",
                        "Document group purposes and membership criteria"
                    ]
                ))
            
            # Check for users with direct policy attachments
            users_with_direct_policies = 0
            try:
                paginator = self.iam.get_paginator('list_users')
                for page in paginator.paginate():
                    for user in page['Users']:
                        attached = self.iam.list_attached_user_policies(UserName=user['UserName'])
                        if attached['AttachedPolicies']:
                            users_with_direct_policies += 1
            except ClientError:
                pass
            
            if users_with_direct_policies > 0:
                self.add_finding(
                    SecurityFinding(
                        finding_id="IAM-GROUP-003",
                        title="Users with direct policy attachments",
                        description=f"Found {users_with_direct_policies} users with policies attached directly instead of through groups",
                        severity=Severity.MEDIUM,
                        resource="IAM Users",
                        recommendation="Move user permissions to groups for better management",
                        risk="Direct policy attachments are harder to manage and audit",
                        compliance=["AWS-WAF-SEC09"]
                    )
                )
                
        except ClientError as e:
            # Silently handle if user doesn't have permissions to list groups
            pass
    
    def show_setup_recommendations(self):
        """Show IAM setup recommendations based on current state."""
        print("\n" + "="*80)
        print("🎯 AWS IAM SETUP RECOMMENDATIONS")
        print("="*80)
        
        # Get groups for analysis
        groups = []
        admin_groups = []
        try:
            paginator = self.iam.get_paginator('list_groups')
            for page in paginator.paginate():
                for group in page['Groups']:
                    group_name = group['GroupName']
                    attached_policies = self.iam.list_attached_group_policies(GroupName=group_name)
                    
                    group_info = {
                        'name': group_name,
                        'attached_policies': [p['PolicyName'] for p in attached_policies['AttachedPolicies']]
                    }
                    groups.append(group_info)
                    
                    # Check if admin group
                    admin_indicators = ['AdministratorAccess', 'PowerUserAccess', 'admin', 'Admin']
                    for policy in group_info['attached_policies']:
                        if any(indicator in policy for indicator in admin_indicators):
                            admin_groups.append(group_info)
                            break
        except ClientError:
            print("⚠️  Unable to retrieve groups")
        
        # Get user count
        user_count = 0
        try:
            paginator = self.iam.get_paginator('list_users')
            for page in paginator.paginate():
                user_count += len(page['Users'])
        except ClientError:
            pass
        
        print(f"\n📋 CURRENT ACCOUNT OVERVIEW:")
        print(f"   • Account ID: {self.account_id}")
        print(f"   • Current User: {self.current_user_name}")
        print(f"   • Is Root User: {'Yes ⚠️' if self.is_root_user else 'No ✓'}")
        print(f"   • Total Users: {user_count}")
        print(f"   • Total Groups: {len(groups)}")
        print(f"   • Admin Groups Found: {len(admin_groups)}")
        
        if admin_groups:
            print(f"\n🔑 EXISTING ADMIN GROUPS:")
            for group in admin_groups[:3]:  # Show first 3
                print(f"   • {group['name']}")
                for policy in group['attached_policies'][:2]:  # Show first 2 policies
                    print(f"     - Policy: {policy}")
        
        print(f"\n💡 RECOMMENDED SETUP STRATEGY:")
        
        if self.is_root_user:
            print("\n   🚨 CRITICAL: Stop using root user immediately!")
            print("   Root user has unrestricted access and should only be used for account management tasks.")
        
        if not admin_groups:
            print("\n   1️⃣  CREATE ADMIN GROUP")
            print("      Create an administrative group for better permission management")
            print("      Group Name: 'Administrators' or 'AdminGroup'")
            print("      Attach Policy: AdministratorAccess")
        else:
            print(f"\n   1️⃣  USE EXISTING ADMIN GROUP: {admin_groups[0]['name']}")
            print("      Add administrative users to this existing group")
        
        print("\n   2️⃣  CREATE ADMINISTRATIVE USER")
        print("      Create a dedicated admin user for daily administrative tasks")
        print("      Enable console access with strong password")
        print("      Add to admin group for permissions")
        
        print("\n   3️⃣  ENABLE MFA FOR ALL USERS")
        print("      Multi-factor authentication adds critical security layer")
        print("      Use virtual MFA device (Google Authenticator, Authy, etc.)")
        print("      Enforce MFA for privileged operations")
        
        print("\n   4️⃣  CREATE LEAST-PRIVILEGE USERS")
        print("      Developer users: PowerUserAccess or specific service access")
        print("      Read-only users: ReadOnlyAccess for auditors")
        print("      Service-specific users: Only required permissions")
        
        print("\n   5️⃣  IMPLEMENT GROUP-BASED PERMISSIONS")
        print("      Suggested groups:")
        print("      • Administrators - Full admin access")
        print("      • Developers - PowerUser or specific service access")
        print("      • ReadOnly - Read access for monitoring/auditing")
        print("      • Billing - Access to billing information only")
        
        if self.is_root_user:
            print("\n   6️⃣  SECURE THE ROOT USER")
            print("      • Enable MFA on root user immediately")
            print("      • Delete any root user access keys")
            print("      • Use strong, unique password")
            print("      • Store credentials in secure password manager")
            print("      • Document password recovery process")
            
            print("\n🚨 ROOT USER TASKS (Only use root for these):")
            print("   • Change account settings (name, email, password)")
            print("   • Close AWS account")
            print("   • Change AWS support plan")
            print("   • Configure MFA delete for S3 buckets")
            print("   • Submit reverse DNS requests")
            print("   • Create CloudFront key pairs")
        
        print("\n📚 BEST PRACTICES:")
        print("   • Use temporary credentials (IAM roles) when possible")
        print("   • Rotate access keys every 90 days")
        print("   • Regular access reviews (quarterly)")
        print("   • Use AWS Organizations for multi-account management")
        print("   • Enable CloudTrail for audit logging")
        print("   • Use IAM Access Analyzer for permissions analysis")
        
        print("\n✅ QUICK START COMMANDS:")
        print("   # List all users")
        print("   aws iam list-users")
        print("\n   # List all groups")
        print("   aws iam list-groups")
        print("\n   # Check MFA devices for a user")
        print("   aws iam list-mfa-devices --user-name <username>")
        
        print(f"\n{'=' * 80}")
        print("END OF RECOMMENDATIONS")
        print(f"{'=' * 80}\n")
    
    def print_human_readable_report(self, analysis_results: Dict[str, Any]):
        """Print a human-readable security report."""
        print(f"\n{'=' * 80}")
        print("AWS IAM SECURITY ANALYSIS REPORT")
        print(f"{'=' * 80}")
        print(f"Account ID: {analysis_results['account_id']}")
        print(f"Analysis Date: {analysis_results['analysis_date']}")
        print(f"Security Score: {analysis_results['security_score']}/100")
        print(f"{'=' * 80}\n")
        
        # Executive Summary
        print("EXECUTIVE SUMMARY")
        print("-" * 40)
        print(analysis_results['executive_summary'])
        print()
        
        # Findings by Severity
        print("\nFINDINGS BY SEVERITY")
        print("-" * 40)
        severity_counts = analysis_results['findings_by_severity']
        for severity, count in severity_counts.items():
            if count > 0:
                icon = self.get_severity_icon(severity)
                print(f"{icon} {severity.upper()}: {count}")
        print()
        
        # Critical and High Findings Detail
        critical_high = [f for f in analysis_results['findings'] 
                        if f.severity in [Severity.CRITICAL, Severity.HIGH]]
        
        if critical_high:
            print("\nCRITICAL & HIGH SEVERITY FINDINGS")
            print("-" * 40)
            for finding in critical_high:
                self.print_finding(finding)
        
        # Recommendations
        if analysis_results['recommendations']:
            print("\nRECOMMENDATIONS")
            print("-" * 40)
            for i, rec in enumerate(analysis_results['recommendations'], 1):
                print(f"\n{i}. {rec.title}")
                print(f"   Severity: {rec.severity.value.upper()}")
                print(f"   Impact: {rec.impact}")
                print(f"   Effort: {rec.effort}")
                print(f"   Description: {rec.description}")
                
                if rec.remediation_steps:
                    print("\n   Steps to remediate:")
                    for step in rec.remediation_steps[:3]:  # Show first 3 steps
                        print(f"   {step.step_number}. {step.description}")
                    if len(rec.remediation_steps) > 3:
                        print(f"   ... and {len(rec.remediation_steps) - 3} more steps")
        
        print(f"\n{'=' * 80}")
        print("END OF REPORT")
        print(f"{'=' * 80}\n")
    
    def print_finding(self, finding: SecurityFinding):
        """Print a single finding in human-readable format."""
        icon = self.get_severity_icon(finding.severity.value)
        print(f"\n{icon} {finding.title}")
        print(f"   ID: {finding.finding_id}")
        print(f"   Resource: {finding.resource}")
        print(f"   Risk: {finding.risk}")
        print(f"   Recommendation: {finding.recommendation}")
        if finding.compliance:
            print(f"   Compliance: {', '.join(finding.compliance)}")
    
    def get_severity_icon(self, severity: str) -> str:
        """Get icon for severity level."""
        icons = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
            "info": "⚪"
        }
        return icons.get(severity, "•")
    
    def save_json_output(self, analysis_results: Dict[str, Any], output_file: str, pretty: bool = False):
        """Save analysis results to JSON file."""
        # Convert findings and recommendations to dictionaries
        recommendations = [r.to_dict() for r in analysis_results['recommendations']]
        
        # Organize execution plan by priority
        execution_plan = {
            "critical": [r for r in recommendations if r['severity'] == 'critical'],
            "high": [r for r in recommendations if r['severity'] == 'high'],
            "medium": [r for r in recommendations if r['severity'] == 'medium'],
            "low": [r for r in recommendations if r['severity'] == 'low']
        }
        
        json_results = {
            "account_id": analysis_results['account_id'],
            "analysis_date": analysis_results['analysis_date'],
            "security_score": analysis_results['security_score'],
            "total_findings": analysis_results['total_findings'],
            "filtered_findings": analysis_results['filtered_findings'],
            "findings_by_severity": analysis_results['findings_by_severity'],
            "executive_summary": analysis_results['executive_summary'],
            "findings": [f.to_dict() for f in analysis_results['findings']],
            "recommendations": recommendations,
            "execution_plan": execution_plan,
            "best_practices": analysis_results.get('best_practices', {})
        }
        
        with open(output_file, 'w') as f:
            if pretty:
                json.dump(json_results, f, indent=2)
            else:
                json.dump(json_results, f)
        
        print(f"Results saved to {output_file}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Comprehensive AWS IAM Security Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run basic security check with human-readable output
  python iam-check.py
  
  # Generate JSON output for automation
  python iam-check.py --json
  
  # Save pretty-printed JSON to file
  python iam-check.py --json --format pretty --output findings.json
  
  # Show only high severity and above findings
  python iam-check.py --severity high
  
  # Generate JSON and filter by severity
  python iam-check.py --json --severity medium --output medium-findings.json
  
  # Analyze only current user (faster)
  python iam-check.py --current-user
  
  # Show setup recommendations only
  python iam-check.py --recommendations
        """
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )
    
    parser.add_argument(
        '--format',
        choices=['compact', 'pretty'],
        default='compact',
        help='JSON output format (default: compact)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Save output to file (use with --json for JSON format, otherwise saves human-readable report)'
    )
    
    parser.add_argument(
        '--severity',
        choices=['critical', 'high', 'medium', 'low', 'info'],
        default='info',
        help='Minimum severity level to include (default: info)'
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
    
    args = parser.parse_args()
    
    # Convert severity string to enum
    min_severity = Severity(args.severity)
    
    # Create and run the checker
    checker = IAMSecurityChecker()
    
    try:
        # Handle different modes
        if args.recommendations:
            # Just show recommendations
            checker.get_current_identity()
            checker.show_setup_recommendations()
        else:
            # Run analysis
            results = checker.run_analysis(
                min_severity=min_severity,
                current_user_only=args.current_user,
                quiet=args.json
            )
            
            if args.json:
                # JSON output mode
                if args.output:
                    checker.save_json_output(results, args.output, pretty=(args.format == 'pretty'))
                else:
                    # Print to stdout
                    recommendations = [r.to_dict() for r in results['recommendations']]
                    execution_plan = {
                        "critical": [r for r in recommendations if r['severity'] == 'critical'],
                        "high": [r for r in recommendations if r['severity'] == 'high'],
                        "medium": [r for r in recommendations if r['severity'] == 'medium'],
                        "low": [r for r in recommendations if r['severity'] == 'low']
                    }
                    
                    json_output = {
                        "account_id": results['account_id'],
                        "analysis_date": results['analysis_date'],
                        "security_score": results['security_score'],
                        "total_findings": results['total_findings'],
                        "filtered_findings": results['filtered_findings'],
                        "findings_by_severity": results['findings_by_severity'],
                        "executive_summary": results['executive_summary'],
                        "findings": [f.to_dict() for f in results['findings']],
                        "recommendations": recommendations,
                        "execution_plan": execution_plan,
                        "best_practices": results.get('best_practices', {})
                    }
                    
                    if args.format == 'pretty':
                        print(json.dumps(json_output, indent=2))
                    else:
                        print(json.dumps(json_output))
            else:
                # Human-readable output
                checker.print_human_readable_report(results)
                
                # If output file specified in non-JSON mode, save report
                if args.output:
                    with open(args.output, 'w') as f:
                        # Redirect print to file
                        import contextlib
                        with contextlib.redirect_stdout(f):
                            checker.print_human_readable_report(results)
                    print(f"\nReport saved to {args.output}")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()