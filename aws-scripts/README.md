# Comprehensive AWS IAM Security Guide

A comprehensive IAM security analysis and remediation toolkit that follows AWS Well-Architected Framework best practices to identify security risks and provide actionable remediation guidance.

## Table of Contents

1. [Overview](#overview)
2. [Script Architecture](#script-architecture)
3. [Features](#features)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Understanding the Output](#understanding-the-output)
7. [JSON Structure](#json-structure)
8. [Automation Guide](#automation-guide)
9. [CI/CD Integration](#cicd-integration)
10. [Minimum IAM Permissions](#minimum-iam-permissions)
11. [Troubleshooting](#troubleshooting)
12. [Best Practices](#best-practices)
13. [References](#references)

## Overview

The AWS IAM Security Toolkit consists of multiple scripts that work together to provide comprehensive IAM security analysis and remediation:

- **`iam-check.py`**: The primary security analysis tool that evaluates your AWS IAM configuration against industry best practices and the AWS Well-Architected Framework
- **`remediation.py`**: Interactive remediation script that processes findings from `iam-check.py` and offers to fix them
- **`iam-auto-remediate.py`**: Automated remediation script that can execute recommended security improvements
- **`a-iam-check.py`**: Alternative IAM checker focused on generating detailed remediation guides

## Script Architecture

### Workflow Options

#### Option 1: Interactive Remediation Workflow
```
iam-check.py → findings.json → remediation.py
(Analysis)   → (Findings)    → (Interactive fixes)
```

#### Option 2: Automated Remediation Workflow
```
a-iam-check.py → iam-guide.json → iam-auto-remediate.py
(Analysis)     → (Remediation guide) → (Automated execution)
```

### Script Comparison

| Script | Purpose | Input | Output | Mode |
|--------|---------|-------|--------|------|
| `iam-check.py` | Comprehensive security analysis | AWS Account | JSON findings with severity levels | Analysis |
| `remediation.py` | Process and fix findings | findings.json | Remediation log | Interactive |
| `iam-auto-remediate.py` | Execute remediation guide | iam-guide.json | Execution log | Automated |
| `a-iam-check.py` | Generate remediation guides | AWS Account | Detailed remediation guide | Analysis |

### Key Benefits

- **Comprehensive Analysis**: Checks over 20 different security aspects of IAM
- **Severity-Based Findings**: Categorizes issues as CRITICAL, HIGH, MEDIUM, LOW, or INFO
- **Actionable Remediation**: Provides step-by-step instructions with AWS CLI commands
- **Automation Ready**: JSON output designed for integration with CI/CD pipelines
- **Security Scoring**: Provides a 0-100 security score for quick assessment
- **Compliance Mapping**: Maps findings to compliance frameworks (CIS, AWS WAF)

## Features

### Security Checks

1. **Root User Security**
   - Detects root user usage
   - Checks for root user MFA
   - Identifies root user access keys

2. **User Security**
   - MFA status for all users
   - Access key age and rotation
   - Unused access keys
   - Inline policy usage

3. **Group Management**
   - Empty groups detection
   - Group-based permission analysis
   - Missing groups identification

4. **Policy Analysis**
   - Wildcard permissions detection
   - Overly permissive policies
   - Least privilege violations

5. **Password Policy**
   - CIS benchmark compliance
   - Password complexity requirements
   - Password expiration settings

6. **Resource Hygiene**
   - Unused roles and users
   - Stale access keys
   - Cross-account access review

7. **Organization Security**
   - Service Control Policy (SCP) usage
   - Organization-level guardrails

### Output Formats

- **Human-Readable Report**: Formatted console output with executive summary
- **JSON Output**: Structured data for automation and integration
- **File Export**: Save results to file for archival or processing

## Installation

### Prerequisites

- Python 3.8+
- AWS CLI configured with appropriate credentials
- boto3 library

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd strands-weather-agent

# Install required packages
pip install boto3

# Verify AWS credentials
aws sts get-caller-identity
```

## Usage

### Workflow 1: Interactive Remediation (Recommended)

```bash
# Step 1: Run comprehensive security analysis
python iam-check.py --json --format pretty --output findings.json

# Step 2: Review findings (optional)
cat findings.json | jq '.findings[] | {id: .finding_id, title: .title, severity: .severity}'

# Step 3: Run interactive remediation
python remediation.py findings.json

# Step 4: Auto-remediate unused roles (optional)
python remediation.py findings.json --auto

# Step 5: Dry-run mode to see what would be done
python remediation.py findings.json --dry-run
```

### Workflow 2: Automated Remediation

```bash
# Step 1: Generate remediation guide
python a-iam-check.py --json-output > iam-guide.json

# Step 2: Review recommendations (dry-run)
python iam-auto-remediate.py --input iam-guide.json --dry-run

# Step 3: Execute remediation (requires confirmation)
python iam-auto-remediate.py --input iam-guide.json --execute

# Step 4: Execute only high priority actions
python iam-auto-remediate.py --input iam-guide.json --execute --priority high
```

### Basic Usage Options

```bash
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
```

### Command Line Options

- `--json`: Output results in JSON format
- `--format [compact|pretty]`: JSON output format (default: compact)
- `--output <filename>`: Save output to file
- `--severity [critical|high|medium|low|info]`: Minimum severity level to include (default: info)
- `--current-user`: Analyze only the current user (faster execution)
- `--recommendations`: Show IAM setup recommendations without full analysis

### Examples

#### Example 1: Quick Security Assessment
```bash
python iam-check.py
```

Output:
```
🔍 Starting comprehensive IAM security analysis...

================================================================================
AWS IAM SECURITY ANALYSIS REPORT
================================================================================
Account ID: 123456789012
Analysis Date: 2024-01-15T10:30:00Z
Security Score: 75/100
================================================================================

EXECUTIVE SUMMARY
----------------------------------------
IAM Security Assessment Summary
Account: 123456789012
Risk Level: HIGH
Security Score: 75/100
Action Required: Urgent remediation needed

Findings Summary:
- Critical: 1
- High: 3
- Medium: 5
- Low: 2
- Info: 1

Top Risks Identified:
- Root user detected
- MFA not enabled for user admin-user
- Old access key for user developer
```

#### Example 2: Generate Automation-Ready JSON
```bash
python iam-check.py --json --format pretty --output iam-findings.json
```

#### Example 3: High-Priority Issues Only
```bash
python iam-check.py --severity high
```

## Understanding the Output

### Security Score

The security score (0-100) provides a quick assessment of your IAM security posture:
- **90-100**: Excellent security posture
- **70-89**: Good security with some improvements needed
- **50-69**: Moderate security risks requiring attention
- **Below 50**: Significant security risks requiring immediate action

### Finding Severity Levels

- **CRITICAL**: Immediate action required (e.g., root user usage, no MFA on privileged accounts)
- **HIGH**: Urgent remediation needed (e.g., old access keys, wildcard permissions)
- **MEDIUM**: Plan remediation activities (e.g., weak password policy, missing groups)
- **LOW**: Review and improve (e.g., unused resources, inline policies)
- **INFO**: Informational findings (e.g., using temporary credentials)

### Executive Summary

Provides a high-level overview including:
- Overall risk assessment
- Security score
- Finding counts by severity
- Top risks identified
- Recommended action level

## JSON Structure

The JSON output is structured for easy parsing and automation:

```json
{
  "account_id": "123456789012",
  "analysis_date": "2024-01-15T10:30:00Z",
  "security_score": 75,
  "total_findings": 12,
  "filtered_findings": 4,
  "findings_by_severity": {
    "critical": 1,
    "high": 3,
    "medium": 5,
    "low": 2,
    "info": 1
  },
  "executive_summary": "IAM Security Assessment Summary...",
  "findings": [
    {
      "finding_id": "IAM-004",
      "title": "Root user detected",
      "description": "You are currently using root user credentials",
      "severity": "critical",
      "resource": "Account 123456789012 root user",
      "recommendation": "Stop using root user immediately and switch to an IAM user or role",
      "risk": "Root user has unrestricted access to all resources and actions",
      "compliance": ["AWS-WAF-SEC03", "CIS-AWS-1.1"],
      "references": ["https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html"]
    }
  ],
  "recommendations": [
    {
      "recommendation_id": "REC-ROOT-001",
      "title": "Secure Root User Account",
      "description": "Implement comprehensive root user security measures",
      "severity": "critical",
      "category": "Identity Security",
      "impact": "Prevents unauthorized access to highest privilege account",
      "effort": "Medium",
      "related_findings": ["IAM-004"],
      "remediation_steps": [
        {
          "step_number": 1,
          "description": "Enable MFA on root user",
          "commands": [],
          "prerequisites": ["Access to root user email", "MFA device or app"],
          "validation": null,
          "rollback": null,
          "estimated_time": "10 minutes",
          "automation_safe": false,
          "requires_human_review": true
        }
      ],
      "alternative_approaches": [
        "Use AWS Organizations to apply SCPs that restrict root user actions"
      ],
      "prevention_tips": [
        "Store root credentials in a secure vault",
        "Regular audit of root user activity"
      ]
    }
  ],
  "execution_plan": {
    "critical": [...],
    "high": [...],
    "medium": [...],
    "low": [...]
  },
  "best_practices": {
    "root_user": [
      "Never use root user for daily tasks",
      "Enable MFA on root user account",
      "Delete all root user access keys"
    ],
    "iam_users": [
      "Enable MFA on all IAM users",
      "Use groups for permission management",
      "Apply least privilege principle"
    ],
    "groups": [...],
    "policies": [...],
    "access_keys": [...],
    "general": [...]
  }
}
```

## Automation Guide

### Remediation Scripts Overview

The toolkit includes two remediation scripts with different approaches:

#### 1. `remediation.py` - Interactive Remediation

Processes findings from `iam-check.py` and offers interactive remediation:

```bash
# Generate findings first
python iam-check.py --json --output findings.json

# Interactive mode - prompts for each finding
python remediation.py findings.json

# Auto-remediate unused roles
python remediation.py findings.json --auto

# Dry run mode (recommended first)
python remediation.py findings.json --dry-run
```

**Features:**
- Interactive prompts for each finding
- Auto-remediation mode for unused roles
- Skips protected AWS-managed resources
- Creates detailed remediation logs
- Safe deletion with policy detachment

**Supported Remediations:**
- Delete unused IAM roles
- Delete stale IAM roles
- Delete empty IAM groups
- Review cross-account access (manual)

#### 2. `iam-auto-remediate.py` - Automated Remediation

Executes remediation guides from `a-iam-check.py`:

```bash
# Generate remediation guide
python a-iam-check.py --json-output > iam-guide.json

# Review what will be done (dry-run)
python iam-auto-remediate.py --input iam-guide.json --dry-run

# Execute remediation with confirmation
python iam-auto-remediate.py --input iam-guide.json --execute

# Execute only critical priority actions
python iam-auto-remediate.py --input iam-guide.json --execute --priority critical
```

**Features:**
- Priority-based execution (critical → high → medium)
- Dry-run mode for testing
- Validation and rollback commands
- Best practices recommendations
- Automated AWS CLI command execution

**Supported Remediations:**
- Create admin users and groups
- Enable MFA on users
- Rotate access keys
- Implement least-privilege access
- Secure root user account

### Python Automation Example

```python
import json
import subprocess
import sys

class IAMSecurityAutomation:
    def __init__(self, findings_file):
        with open(findings_file, 'r') as f:
            self.data = json.load(f)
    
    def get_critical_findings(self):
        """Get all critical severity findings."""
        return [f for f in self.data['findings'] if f['severity'] == 'critical']
    
    def get_high_risk_users(self):
        """Identify users with high-risk configurations."""
        high_risk_users = []
        for finding in self.data['findings']:
            if 'MFA not enabled' in finding['title'] or 'Old access key' in finding['title']:
                # Extract username from resource field
                if 'User:' in finding['resource']:
                    username = finding['resource'].split('User: ')[1].split(',')[0]
                    high_risk_users.append({
                        'username': username,
                        'issue': finding['title'],
                        'severity': finding['severity']
                    })
        return high_risk_users
    
    def execute_remediation(self, recommendation_id):
        """Execute remediation steps for a specific recommendation."""
        recommendation = next(
            (r for r in self.data['recommendations'] if r['recommendation_id'] == recommendation_id),
            None
        )
        
        if not recommendation:
            print(f"Recommendation {recommendation_id} not found")
            return False
        
        print(f"\nExecuting remediation: {recommendation['title']}")
        print(f"Impact: {recommendation['impact']}")
        
        for step in recommendation['remediation_steps']:
            if step['automation_safe']:
                print(f"\nStep {step['step_number']}: {step['description']}")
                
                # Check prerequisites
                if step['prerequisites']:
                    print("Prerequisites:", ', '.join(step['prerequisites']))
                    if not self.confirm("Prerequisites met?"):
                        print("Skipping step due to unmet prerequisites")
                        continue
                
                # Execute commands
                for cmd in step['commands']:
                    if cmd.startswith('#'):
                        print(f"Manual action required: {cmd}")
                    else:
                        if self.confirm(f"Execute: {cmd}"):
                            self.run_command(cmd)
                
                # Run validation
                if step['validation']:
                    print("Running validation...")
                    self.run_command(step['validation'])
            else:
                print(f"\nStep {step['step_number']}: {step['description']} (MANUAL)")
                print("This step requires manual intervention")
                for cmd in step['commands']:
                    print(f"  {cmd}")
    
    def run_command(self, cmd):
        """Execute a shell command safely."""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Success: {result.stdout}")
            else:
                print(f"❌ Error: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            return False
    
    def confirm(self, message):
        """Ask for user confirmation."""
        response = input(f"{message} (y/n): ").lower().strip()
        return response == 'y'
    
    def generate_summary_report(self):
        """Generate a summary report of findings."""
        print("\n" + "=" * 60)
        print("IAM SECURITY SUMMARY REPORT")
        print("=" * 60)
        print(f"Account: {self.data['account_id']}")
        print(f"Security Score: {self.data['security_score']}/100")
        print(f"Total Findings: {self.data['total_findings']}")
        
        print("\nFindings by Severity:")
        for severity, count in self.data['findings_by_severity'].items():
            print(f"  {severity.upper()}: {count}")
        
        print("\nTop Recommendations:")
        for rec in self.data['recommendations'][:3]:
            print(f"  - {rec['title']} ({rec['severity']})")
            print(f"    Impact: {rec['impact']}")
            print(f"    Effort: {rec['effort']}")

# Usage example
if __name__ == "__main__":
    automation = IAMSecurityAutomation('iam-findings.json')
    
    # Generate summary
    automation.generate_summary_report()
    
    # Get critical findings
    critical = automation.get_critical_findings()
    if critical:
        print(f"\n⚠️  Found {len(critical)} CRITICAL findings!")
        for finding in critical:
            print(f"  - {finding['title']}")
    
    # Identify high-risk users
    high_risk_users = automation.get_high_risk_users()
    if high_risk_users:
        print(f"\n👤 High-risk users identified:")
        for user in high_risk_users:
            print(f"  - {user['username']}: {user['issue']}")
    
    # Execute specific remediation
    if critical and automation.confirm("\nExecute root user remediation?"):
        automation.execute_remediation("REC-ROOT-001")
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: IAM Security Check

on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly on Mondays at 9 AM
  workflow_dispatch:

jobs:
  iam-security-check:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      issues: write
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
        aws-region: us-east-1
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install boto3
    
    - name: Run IAM Security Check
      id: security-check
      run: |
        python iam-check.py --json --output iam-findings.json
        
        # Extract key metrics
        SCORE=$(jq '.security_score' iam-findings.json)
        CRITICAL=$(jq '.findings_by_severity.critical' iam-findings.json)
        HIGH=$(jq '.findings_by_severity.high' iam-findings.json)
        
        echo "score=$SCORE" >> $GITHUB_OUTPUT
        echo "critical=$CRITICAL" >> $GITHUB_OUTPUT
        echo "high=$HIGH" >> $GITHUB_OUTPUT
        
        # Fail if critical findings
        if [ "$CRITICAL" -gt 0 ]; then
          echo "❌ Critical security findings detected!"
          exit 1
        fi
    
    - name: Upload findings
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: iam-security-findings
        path: iam-findings.json
    
    - name: Create issue for findings
      if: failure()
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const findings = JSON.parse(fs.readFileSync('iam-findings.json', 'utf8'));
          
          const critical = findings.findings.filter(f => f.severity === 'critical');
          const high = findings.findings.filter(f => f.severity === 'high');
          
          let issueBody = `## IAM Security Alert 🚨\n\n`;
          issueBody += `**Security Score**: ${findings.security_score}/100\n\n`;
          issueBody += `### Critical Findings (${critical.length})\n`;
          
          critical.forEach(f => {
            issueBody += `- **${f.title}**\n`;
            issueBody += `  - Resource: ${f.resource}\n`;
            issueBody += `  - Risk: ${f.risk}\n`;
            issueBody += `  - Recommendation: ${f.recommendation}\n\n`;
          });
          
          issueBody += `### High Severity Findings (${high.length})\n`;
          high.slice(0, 5).forEach(f => {
            issueBody += `- ${f.title}\n`;
          });
          
          if (high.length > 5) {
            issueBody += `\n_...and ${high.length - 5} more high severity findings_\n`;
          }
          
          github.rest.issues.create({
            owner: context.repo.owner,
            repo: context.repo.repo,
            title: `IAM Security Alert: ${critical.length} critical findings`,
            body: issueBody,
            labels: ['security', 'iam', 'critical']
          });
    
    - name: Post to Slack
      if: failure()
      uses: 8398a7/action-slack@v3
      with:
        status: custom
        custom_payload: |
          {
            "channel": "#security-alerts",
            "attachments": [{
              "color": "danger",
              "title": "IAM Security Check Failed",
              "fields": [
                {
                  "title": "Security Score",
                  "value": "${{ steps.security-check.outputs.score }}/100",
                  "short": true
                },
                {
                  "title": "Critical Findings",
                  "value": "${{ steps.security-check.outputs.critical }}",
                  "short": true
                },
                {
                  "title": "High Findings",
                  "value": "${{ steps.security-check.outputs.high }}",
                  "short": true
                }
              ]
            }]
          }
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    
    triggers {
        cron('H 9 * * 1')  // Weekly on Mondays
    }
    
    environment {
        AWS_DEFAULT_REGION = 'us-east-1'
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install boto3
                '''
            }
        }
        
        stage('IAM Security Check') {
            steps {
                withAWS(credentials: 'aws-iam-checker', region: 'us-east-1') {
                    script {
                        def result = sh(
                            script: '''
                                . venv/bin/activate
                                python iam-check.py --json --output iam-findings.json
                                cat iam-findings.json | jq '.security_score'
                            ''',
                            returnStdout: true
                        ).trim()
                        
                        def findings = readJSON file: 'iam-findings.json'
                        
                        if (findings.findings_by_severity.critical > 0) {
                            error("Critical IAM security findings detected!")
                        }
                        
                        if (findings.security_score < 70) {
                            unstable("IAM security score below threshold: ${findings.security_score}/100")
                        }
                    }
                }
            }
        }
        
        stage('Archive Results') {
            steps {
                archiveArtifacts artifacts: 'iam-findings.json', fingerprint: true
                
                publishHTML target: [
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.',
                    reportFiles: 'iam-findings.json',
                    reportName: 'IAM Security Report'
                ]
            }
        }
    }
    
    post {
        failure {
            emailext (
                subject: "IAM Security Check Failed - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: '''
                    <h2>IAM Security Check Failed</h2>
                    <p>Critical security findings were detected in the AWS account.</p>
                    <p>View the full report: ${BUILD_URL}</p>
                ''',
                to: 'security-team@example.com',
                mimeType: 'text/html'
            )
        }
        
        unstable {
            emailext (
                subject: "IAM Security Score Below Threshold - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: 'IAM security score is below the acceptable threshold of 70.',
                to: 'security-team@example.com'
            )
        }
    }
}
```

## Minimum IAM Permissions

To run the IAM Security Checker, the following minimum IAM permissions are required:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "IAMReadOnly",
            "Effect": "Allow",
            "Action": [
                "iam:GetAccountPasswordPolicy",
                "iam:GetAccountSummary",
                "iam:GetCredentialReport",
                "iam:GenerateCredentialReport",
                "iam:GetGroup",
                "iam:GetPolicy",
                "iam:GetPolicyVersion",
                "iam:GetRole",
                "iam:GetUser",
                "iam:ListAccessKeys",
                "iam:ListAttachedGroupPolicies",
                "iam:ListAttachedRolePolicies",
                "iam:ListAttachedUserPolicies",
                "iam:ListGroups",
                "iam:ListGroupsForUser",
                "iam:ListMFADevices",
                "iam:ListPolicies",
                "iam:ListRoles",
                "iam:ListUserPolicies",
                "iam:ListUsers"
            ],
            "Resource": "*"
        },
        {
            "Sid": "STSReadOnly",
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        },
        {
            "Sid": "OrganizationsReadOnly",
            "Effect": "Allow",
            "Action": [
                "organizations:DescribeOrganization",
                "organizations:ListPolicies"
            ],
            "Resource": "*"
        }
    ]
}
```

### Creating a Read-Only IAM Role

```bash
# Create the policy
aws iam create-policy \
    --policy-name IAMSecurityCheckerPolicy \
    --policy-document file://iam-checker-policy.json

# Create the role
aws iam create-role \
    --role-name IAMSecurityChecker \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach the policy to the role
aws iam attach-role-policy \
    --role-name IAMSecurityChecker \
    --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/IAMSecurityCheckerPolicy
```

## Troubleshooting

### Common Issues

#### 1. No AWS Credentials Found
```
❌ Error: No AWS credentials found. Please configure AWS credentials.
```

**Solution:**
```bash
# Configure AWS CLI
aws configure

# Or export credentials
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

#### 2. Insufficient Permissions
```
❌ Error: Unable to list IAM users: An error occurred (AccessDenied)
```

**Solution:**
Ensure your IAM user/role has the required permissions listed in the [Minimum IAM Permissions](#minimum-iam-permissions) section.

#### 3. Credential Report Timeout
```
⚠️  Credential report generation timeout
```

**Solution:**
The credential report may take time to generate for large accounts. Try:
```bash
# Pre-generate the report
aws iam generate-credential-report

# Wait a moment, then run the checker
sleep 5
python iam-check.py
```

#### 4. JSON Parsing Errors
```
json.decoder.JSONDecodeError: Expecting value: line 1 column 1
```

**Solution:**
Ensure the JSON file is valid:
```bash
# Validate JSON
python -m json.tool iam-findings.json

# Or use jq
jq . iam-findings.json
```

### Debug Mode

For detailed debugging information:
```bash
# Set Python logging level
export LOG_LEVEL=DEBUG

# Run with Python debug flag
python -u iam-check.py
```

## Best Practices

### 1. Regular Scanning
- Run security checks at least weekly
- Integrate with CI/CD pipelines
- Set up automated alerts for critical findings

### 2. Progressive Remediation
- Start with CRITICAL findings
- Address HIGH severity issues next
- Plan MEDIUM remediation in sprints
- Review LOW findings quarterly

### 3. Automation Safety
- Always run in dry-run mode first
- Test remediation in non-production accounts
- Have rollback plans ready
- Document all changes

### 4. Continuous Improvement
- Track security score trends
- Set score thresholds (e.g., minimum 80)
- Regular review of new AWS features
- Update checker for new best practices

### 5. Team Collaboration
- Share findings with development teams
- Provide security training based on common findings
- Create runbooks for remediation
- Celebrate security improvements

## References

### AWS Documentation
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Well-Architected Framework - Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
- [AWS Security Best Practices](https://aws.amazon.com/architecture/security-identity-compliance/)

### Compliance Frameworks
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [AWS Security Hub Standards](https://docs.aws.amazon.com/securityhub/latest/userguide/standards.html)

### Additional Resources
- [AWS re:Post IAM Topics](https://repost.aws/topics/TAgOdRefu6ShempO3dWPEofg/iam)
- [AWS Security Blog](https://aws.amazon.com/blogs/security/)
- [Open Source Security Tools](https://github.com/toniblyx/prowler)

---

## Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Contact the security team
- Check the troubleshooting guide

---

**Remember**: Security is a journey, not a destination. Regular assessment and continuous improvement are key to maintaining a strong security posture.