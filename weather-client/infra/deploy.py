#!/usr/bin/env python3
"""Simple deployment script for Hello World Lambda CDK Stack"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def deploy(environment: str = "dev", destroy: bool = False, auto_approve: bool = False):
    """Deploy or destroy the CDK stack"""
    
    # Set environment
    stack_name = f"HelloWorldLambdaStack-{environment}"
    os.environ["ENVIRONMENT"] = environment
    
    # Run validate setup script to ensure CDK is bootstrapped
    print("🔧 Running setup validation...")
    subprocess.run(["bash", "validate-setup.sh"], check=True)
    
    # Get python path from virtual environment
    venv_python = ".venv/bin/python" if os.path.exists(".venv/bin/python") else "python3"
    
    if destroy:
        print(f"🗑️  Destroying stack: {stack_name}")
        subprocess.run([
            "cdk", "destroy", stack_name,
            "--app", f"{venv_python} app_with_nag.py",
            "--force"
        ], check=True)
    else:
        print(f"🚀 Deploying stack: {stack_name}")
        deploy_cmd = [
            "cdk", "deploy", stack_name,
            "--app", f"{venv_python} app_with_nag.py"
        ]
        if auto_approve:
            deploy_cmd.append("--require-approval=never")
        
        subprocess.run(deploy_cmd, check=True)
        
        # Get stack outputs
        print("\n📋 Stack deployed successfully!")
        subprocess.run([
            "aws", "cloudformation", "describe-stacks",
            "--stack-name", stack_name,
            "--query", "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue",
            "--output", "text"
        ], check=False)


def main():
    parser = argparse.ArgumentParser(description="Deploy Hello World Lambda CDK Stack")
    parser.add_argument("--environment", "-e", default="dev", help="Environment (dev/staging/prod)")
    parser.add_argument("--destroy", action="store_true", help="Destroy the stack")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve deployment")
    
    args = parser.parse_args()
    
    try:
        deploy(args.environment, args.destroy, args.auto_approve)
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()