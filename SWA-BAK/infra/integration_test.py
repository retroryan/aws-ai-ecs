#!/usr/bin/env python3
"""
Integration Test for Strands Weather Agent with Langfuse Telemetry
Validates the full deployment with and without telemetry
"""

import json
import sys
import time
import subprocess
from pathlib import Path
import boto3
import requests
from datetime import datetime


class IntegrationTester:
    """Integration test suite for telemetry validation"""
    
    def __init__(self, region="us-east-1"):
        self.region = region
        self.cfn = boto3.client("cloudformation", region_name=region)
        self.ssm = boto3.client("ssm", region_name=region)
        self.results = []
        
    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        emoji = "✅" if passed else "❌"
        print(f"{emoji} {test_name}: {details}")
    
    def test_cloudformation_parameters(self):
        """Test CloudFormation parameter configuration"""
        print("\n🔍 Testing CloudFormation Parameters...")
        
        try:
            stack = self.cfn.describe_stacks(StackName="strands-weather-agent-services")["Stacks"][0]
            params = {p["ParameterKey"]: p["ParameterValue"] for p in stack["Parameters"]}
            
            # Check telemetry parameter
            if "EnableTelemetry" in params:
                enabled = params["EnableTelemetry"] == "true"
                self.log_result(
                    "Telemetry Parameter", 
                    True,
                    f"EnableTelemetry = {params['EnableTelemetry']}"
                )
                
                # If enabled, check other params
                if enabled and "LangfuseHost" in params and params["LangfuseHost"]:
                    self.log_result(
                        "Langfuse Host", 
                        True,
                        f"Configured: {params['LangfuseHost']}"
                    )
                else:
                    self.log_result(
                        "Langfuse Host",
                        not enabled,  # Pass if telemetry is disabled
                        "Not configured (telemetry disabled)" if not enabled else "Missing"
                    )
            else:
                self.log_result("Telemetry Parameter", False, "Not found in stack")
                
        except Exception as e:
            self.log_result("CloudFormation Stack", False, str(e))
    
    def test_parameter_store(self):
        """Test Parameter Store credentials"""
        print("\n🔐 Testing Parameter Store...")
        
        try:
            # Check if parameters exist
            param_names = [
                "/strands-weather-agent/langfuse/public-key",
                "/strands-weather-agent/langfuse/secret-key"
            ]
            
            for param_name in param_names:
                try:
                    self.ssm.get_parameter(Name=param_name, WithDecryption=True)
                    self.log_result(
                        f"Parameter {param_name.split('/')[-1]}", 
                        True, 
                        "Exists and encrypted"
                    )
                except self.ssm.exceptions.ParameterNotFound:
                    self.log_result(
                        f"Parameter {param_name.split('/')[-1]}", 
                        False, 
                        "Not found (run deploy.py to create)"
                    )
                except Exception as e:
                    self.log_result(
                        f"Parameter {param_name.split('/')[-1]}", 
                        False, 
                        f"Error: {str(e)}"
                    )
                    
        except Exception as e:
            self.log_result("Parameter Store Access", False, str(e))
    
    def test_service_connectivity(self):
        """Test service endpoints"""
        print("\n🌐 Testing Service Connectivity...")
        
        # Get ALB URL
        try:
            stack = self.cfn.describe_stacks(StackName="strands-weather-agent-base")["Stacks"][0]
            alb_url = None
            for output in stack["Outputs"]:
                if output["OutputKey"] == "ALBDNSName":
                    alb_url = f"http://{output['OutputValue']}"
                    break
            
            if not alb_url:
                self.log_result("ALB URL", False, "Not found in outputs")
                return
                
            self.log_result("ALB URL", True, alb_url)
            
            # Test health endpoint
            try:
                resp = requests.get(f"{alb_url}/health", timeout=10)
                self.log_result(
                    "Health Endpoint", 
                    resp.status_code == 200,
                    f"Status: {resp.status_code}"
                )
            except Exception as e:
                self.log_result("Health Endpoint", False, str(e))
            
            # Test query with telemetry check
            try:
                resp = requests.post(
                    f"{alb_url}/query",
                    json={"query": "Test query for telemetry validation"},
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    telemetry_active = data.get("telemetry_enabled", False)
                    self.log_result(
                        "Query Endpoint", 
                        True,
                        f"Telemetry: {'Active' if telemetry_active else 'Inactive'}"
                    )
                else:
                    self.log_result("Query Endpoint", False, f"Status: {resp.status_code}")
            except Exception as e:
                self.log_result("Query Endpoint", False, str(e))
                
        except Exception as e:
            self.log_result("Service Discovery", False, str(e))
    
    def test_deployment_scenarios(self):
        """Test different deployment scenarios"""
        print("\n🚀 Testing Deployment Scenarios...")
        
        # This would typically test actual deployment, but for demo we just check current state
        try:
            stack = self.cfn.describe_stacks(StackName="strands-weather-agent-services")["Stacks"][0]
            stack_status = stack["StackStatus"]
            
            if stack_status in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]:
                self.log_result(
                    "Stack Deployment", 
                    True,
                    f"Status: {stack_status}"
                )
            else:
                self.log_result(
                    "Stack Deployment", 
                    False,
                    f"Unexpected status: {stack_status}"
                )
                
        except Exception as e:
            self.log_result("Stack Status", False, str(e))
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("📋 Integration Test Report")
        print("=" * 60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total == passed:
            print("\n🎉 All integration tests passed!")
            print("\n📊 Next Steps:")
            print("1. Run demo: python3 infra/demo_telemetry.py")
            print("2. Check Langfuse dashboard for traces")
            print("3. Review CloudWatch logs for detailed telemetry")
        else:
            print("\n⚠️  Some tests failed. Review the output above.")
            print("\nCommon fixes:")
            print("- Ensure deployment completed: python3 infra/deploy.py status")
            print("- Check cloud.env exists with valid credentials")
            print("- Verify services are running: python3 infra/test_services.py")
        
        return total == passed
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🧪 Strands Weather Agent - Integration Test Suite")
        print("Testing telemetry integration and deployment validation")
        print("=" * 60)
        
        # Run test suites
        self.test_cloudformation_parameters()
        self.test_parameter_store()
        self.test_service_connectivity()
        self.test_deployment_scenarios()
        
        # Generate report
        return self.generate_report()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Integration tests for Strands Weather Agent telemetry"
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    
    args = parser.parse_args()
    
    tester = IntegrationTester(args.region)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()