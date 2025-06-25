#!/usr/bin/env python3
"""
Model Compliance Testing Script
Tests structured output compliance across all available AWS Bedrock models
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import traceback
from dataclasses import dataclass, field
from pathlib import Path

# Add parent directory to path for imports to avoid relative import issues
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Now import from weather_agent as a package
from weather_agent.mcp_agent import MCPWeatherAgent
from weather_agent.models.structured_responses import WeatherQueryResponse, ExtractedLocation


@dataclass
class TestResult:
    """Result of a single test query"""
    query: str
    category: str
    success: bool
    score: float
    issues: List[str] = field(default_factory=list)
    elapsed_ms: float = 0
    error: Optional[str] = None


@dataclass
class ModelTestResult:
    """Complete test results for a model"""
    model_id: str
    model_name: str
    description: str
    test_results: List[TestResult] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)
    overall_score: float = 0
    success_rate: float = 0
    avg_response_time: float = 0
    summary: str = ""
    test_status: str = "pending"  # pending, completed, failed


class ModelComplianceTester:
    """Test structured output compliance across AWS Bedrock models"""
    
    # Test queries organized by category
    TEST_QUERIES = {
        "simple_location": [
            "What's the weather in New York?",
            "Temperature in Tokyo",
            "Current conditions in London"
        ],
        "coordinate_extraction": [
            "Weather for Chicago, Illinois",
            "Forecast for Paris, France",
            "Conditions in Sydney, Australia"
        ],
        "multi_location": [
            "Compare weather in Seattle and Miami",
            "Temperature differences between Boston and Los Angeles"
        ],
        "agricultural": [
            "Can I plant tomatoes in Des Moines, Iowa?",
            "Frost risk for crops in Minneapolis, Minnesota"
        ],
        "ambiguous": [
            "Weather in Springfield",
            "Temperature in Washington"
        ]
    }
    
    # Models to test with metadata
    MODELS_TO_TEST = [
        # Anthropic Claude Models
        {
            "id": "anthropic.claude-sonnet-4-20250514-v1:0",
            "name": "Claude Sonnet 4",
            "provider": "Anthropic",
            "description": "Newest Claude 4 model, cutting-edge capabilities"
        },
        {
            "id": "anthropic.claude-3-7-sonnet-20250219-v1:0",
            "name": "Claude 3.7 Sonnet",
            "provider": "Anthropic",
            "description": "Latest Claude 3.x model, excellent structured output compliance"
        },
        {
            "id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "name": "Claude 3.5 Sonnet v2",
            "provider": "Anthropic",
            "description": "Strong structured output support, cost-effective"
        },
        {
            "id": "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "name": "Claude 3.5 Sonnet v1",
            "provider": "Anthropic",
            "description": "Proven reliable, tested extensively"
        },
        {
            "id": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "name": "Claude 3.5 Haiku",
            "provider": "Anthropic",
            "description": "Fast and cost-effective, may struggle with complex output"
        },
        {
            "id": "anthropic.claude-3-opus-20240229-v1:0",
            "name": "Claude 3 Opus",
            "provider": "Anthropic",
            "description": "Most capable Claude 3 model, older architecture"
        },
        
        # Amazon Nova Models
        {
            "id": "amazon.nova-premier-v1:0",
            "name": "Nova Premier",
            "provider": "Amazon",
            "description": "Amazon's flagship model for complex tasks"
        },
        {
            "id": "amazon.nova-pro-v1:0",
            "name": "Nova Pro",
            "provider": "Amazon",
            "description": "Balanced performance and cost"
        },
        {
            "id": "amazon.nova-lite-v1:0",
            "name": "Nova Lite",
            "provider": "Amazon",
            "description": "Fast but may struggle with structured output"
        },
        {
            "id": "amazon.nova-micro-v1:0",
            "name": "Nova Micro",
            "provider": "Amazon",
            "description": "Fastest Nova model, limited capabilities"
        },
        
        # Meta Llama Models
        {
            "id": "meta.llama3-3-70b-instruct-v1:0",
            "name": "Llama 3.3 70B",
            "provider": "Meta",
            "description": "Latest Llama model, good open-source alternative"
        },
        {
            "id": "meta.llama3-2-90b-instruct-v1:0",
            "name": "Llama 3.2 90B",
            "provider": "Meta",
            "description": "Larger parameter count for complex reasoning"
        },
        {
            "id": "meta.llama3-1-405b-instruct-v1:0",
            "name": "Llama 3.1 405B",
            "provider": "Meta",
            "description": "Largest Llama model, best reasoning capabilities"
        },
        {
            "id": "meta.llama3-1-70b-instruct-v1:0",
            "name": "Llama 3.1 70B",
            "provider": "Meta",
            "description": "Good balance of capability and speed"
        },
        
        # Cohere Models
        {
            "id": "cohere.command-r-plus-v1:0",
            "name": "Command R+",
            "provider": "Cohere",
            "description": "Strong at retrieval and factual responses"
        },
        {
            "id": "cohere.command-r-v1:0",
            "name": "Command R",
            "provider": "Cohere",
            "description": "Balanced Cohere model, decent structured output"
        },
        
        # Mistral Models
        {
            "id": "mistral.mistral-large-2407-v1:0",
            "name": "Mistral Large",
            "provider": "Mistral",
            "description": "Most capable Mistral model, good instruction following"
        },
        {
            "id": "mistral.mixtral-8x7b-instruct-v0:1",
            "name": "Mixtral 8x7B",
            "provider": "Mistral",
            "description": "Mixture of experts, efficient and capable"
        }
    ]
    
    # Expected coordinates for validation
    EXPECTED_COORDINATES = {
        "new york": (40.7128, -74.0060),
        "tokyo": (35.6762, 139.6503),
        "london": (51.5074, -0.1278),
        "chicago": (41.8781, -87.6298),
        "paris": (48.8566, 2.3522),
        "sydney": (-33.8688, 151.2093),
        "seattle": (47.6062, -122.3321),
        "miami": (25.7617, -80.1918),
        "boston": (42.3601, -71.0589),
        "los angeles": (34.0522, -118.2437),
        "des moines": (41.5868, -93.6250),
        "minneapolis": (44.9778, -93.2650)
    }
    
    def __init__(self, output_dir: str = "test_results"):
        """Initialize the tester with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[ModelTestResult] = []
        self.start_time = datetime.now()
        
    async def test_single_query(self, agent: MCPWeatherAgent, query: str, category: str) -> TestResult:
        """Test a single query against a model"""
        print(f"    Testing: {query}")
        
        result = TestResult(query=query, category=category, success=False, score=0)
        
        try:
            start_time = datetime.now()
            
            # Get structured response
            response = await agent.query_structured(query)
            
            result.elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Evaluate response
            result.score, result.issues = self.evaluate_response(response, query)
            result.success = result.score >= 70  # 70% threshold for success
            
            print(f"      Score: {result.score:.1f}% | Time: {result.elapsed_ms:.0f}ms | Success: {'✅' if result.success else '❌'}")
            if result.issues:
                print(f"      Issues: {', '.join(result.issues[:2])}")  # Show first 2 issues
                
        except Exception as e:
            result.error = str(e)
            result.success = False
            result.score = 0
            print(f"      ERROR: {str(e)[:100]}")
            
        return result
    
    def evaluate_response(self, response: WeatherQueryResponse, query: str) -> Tuple[float, List[str]]:
        """Evaluate a structured response for compliance"""
        score = 100.0
        issues = []
        
        # Check required field: summary
        if not response.summary or len(response.summary.strip()) < 10:
            score -= 20
            issues.append("Missing or inadequate summary")
        
        # Check required field: query_type
        if not response.query_type or response.query_type == "unknown":
            score -= 10
            issues.append(f"Invalid query_type: {response.query_type}")
        
        # Check locations extraction
        if not response.locations:
            score -= 30
            issues.append("No locations extracted")
        else:
            # Check each location
            for loc in response.locations:
                # Check location name
                if not loc.name or loc.name.lower() == "unknown":
                    score -= 10
                    issues.append(f"Invalid location name: '{loc.name}'")
                
                # Check coordinates
                if loc.latitude == 0 and loc.longitude == 0:
                    score -= 15
                    issues.append(f"Missing coordinates for {loc.name}")
                else:
                    # Validate coordinate accuracy if we have expected values
                    loc_key = loc.name.lower().split(',')[0].strip()
                    if loc_key in self.EXPECTED_COORDINATES:
                        expected_lat, expected_lon = self.EXPECTED_COORDINATES[loc_key]
                        lat_diff = abs(loc.latitude - expected_lat)
                        lon_diff = abs(loc.longitude - expected_lon)
                        
                        if lat_diff > 0.5 or lon_diff > 0.5:
                            score -= 10
                            issues.append(f"Inaccurate coordinates for {loc.name}: ({loc.latitude:.2f}, {loc.longitude:.2f})")
                
                # Check timezone
                if not hasattr(loc, 'timezone') or not loc.timezone:
                    score -= 5
                    issues.append(f"Missing timezone for {loc.name}")
                
                # Check confidence (if available)
                if hasattr(loc, 'confidence') and loc.confidence < 0.5:
                    score -= 5
                    issues.append(f"Low confidence ({loc.confidence:.2f}) for {loc.name}")
        
        # Ensure score doesn't go below 0
        return max(0, score), issues
    
    async def test_model(self, model_info: Dict[str, str]) -> ModelTestResult:
        """Test a single model across all query categories"""
        model_id = model_info["id"]
        model_name = model_info["name"]
        
        print(f"\n{'='*80}")
        print(f"Testing Model: {model_name}")
        print(f"Model ID: {model_id}")
        print(f"Provider: {model_info['provider']}")
        print(f"Description: {model_info['description']}")
        print('='*80)
        
        result = ModelTestResult(
            model_id=model_id,
            model_name=model_name,
            description=model_info['description']
        )
        
        try:
            # Override environment variable temporarily
            original_model = os.environ.get('BEDROCK_MODEL_ID')
            os.environ['BEDROCK_MODEL_ID'] = model_id
            
            # Initialize agent
            print("Initializing agent...")
            agent = MCPWeatherAgent(debug_logging=False)
            
            # Test each category
            for category, queries in self.TEST_QUERIES.items():
                print(f"\n  Category: {category}")
                category_results = []
                
                for query in queries:
                    test_result = await self.test_single_query(agent, query, category)
                    result.test_results.append(test_result)
                    category_results.append(test_result)
                
                # Calculate category score
                if category_results:
                    category_score = sum(r.score for r in category_results) / len(category_results)
                    category_success_rate = sum(1 for r in category_results if r.success) / len(category_results) * 100
                    result.category_scores[category] = category_score
                    print(f"  Category Score: {category_score:.1f}% | Success Rate: {category_success_rate:.1f}%")
            
            # Calculate overall metrics
            if result.test_results:
                result.overall_score = sum(r.score for r in result.test_results) / len(result.test_results)
                result.success_rate = sum(1 for r in result.test_results if r.success) / len(result.test_results) * 100
                result.avg_response_time = sum(r.elapsed_ms for r in result.test_results) / len(result.test_results)
            
            result.test_status = "completed"
            result.summary = self.generate_model_summary(result)
            
            print(f"\nOverall Score: {result.overall_score:.1f}% | Success Rate: {result.success_rate:.1f}%")
            print(f"Summary: {result.summary}")
            
        except Exception as e:
            print(f"\nFAILED TO TEST MODEL: {str(e)}")
            traceback.print_exc()
            result.test_status = "failed"
            result.summary = f"Testing failed: {str(e)}"
        
        finally:
            # Restore original model
            if original_model:
                os.environ['BEDROCK_MODEL_ID'] = original_model
            elif 'BEDROCK_MODEL_ID' in os.environ:
                del os.environ['BEDROCK_MODEL_ID']
        
        return result
    
    def generate_model_summary(self, result: ModelTestResult) -> str:
        """Generate a summary of model performance"""
        score = result.overall_score
        success_rate = result.success_rate
        
        if score >= 90 and success_rate >= 90:
            return "Excellent structured output compliance. Production ready."
        elif score >= 80 and success_rate >= 80:
            return "Very good compliance. Minor prompt adjustments recommended."
        elif score >= 70 and success_rate >= 70:
            return "Good compliance with some issues. Prompt engineering needed."
        elif score >= 60:
            return "Moderate compliance. Significant prompt optimization required."
        elif score >= 50:
            return "Limited structured output support. Consider fallback strategies."
        else:
            return "Poor structured output support. Not recommended for this use case."
    
    async def run_all_tests(self, models_to_test: Optional[List[str]] = None):
        """Run tests on all or selected models"""
        print(f"\n{'#'*80}")
        print(f"# AWS Bedrock Model Compliance Testing")
        print(f"# Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"# Total Models: {len(self.MODELS_TO_TEST)}")
        print(f"# Total Queries: {sum(len(q) for q in self.TEST_QUERIES.values())}")
        print(f"{'#'*80}")
        
        # Filter models if specific ones requested
        models = self.MODELS_TO_TEST
        if models_to_test:
            models = [m for m in models if m["id"] in models_to_test or m["name"] in models_to_test]
        
        # Test each model
        for i, model_info in enumerate(models, 1):
            print(f"\n[{i}/{len(models)}] Testing {model_info['name']}...")
            
            try:
                result = await self.test_model(model_info)
                self.results.append(result)
            except Exception as e:
                print(f"Critical error testing {model_info['name']}: {str(e)}")
                # Add failed result
                failed_result = ModelTestResult(
                    model_id=model_info["id"],
                    model_name=model_info["name"],
                    description=model_info["description"],
                    test_status="failed",
                    summary=f"Critical failure: {str(e)}"
                )
                self.results.append(failed_result)
        
        # Generate reports
        self.generate_reports()
    
    def generate_reports(self):
        """Generate comprehensive test reports"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Sort results by overall score
        sorted_results = sorted(self.results, key=lambda x: x.overall_score, reverse=True)
        
        # Generate console summary
        print(f"\n{'#'*80}")
        print(f"# TEST SUMMARY")
        print(f"# Duration: {duration:.1f} seconds")
        print(f"# Models Tested: {len(self.results)}")
        print(f"{'#'*80}")
        
        # Generate markdown report
        report_path = self.output_dir / f"model_compliance_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_path, "w") as f:
            # Header
            f.write("# AWS Bedrock Model Compliance Test Report\n\n")
            f.write(f"**Test Date**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Duration**: {duration:.1f} seconds\n")
            f.write(f"**Models Tested**: {len(self.results)}\n")
            f.write(f"**Total Queries**: {sum(len(q) for q in self.TEST_QUERIES.values())} queries across {len(self.TEST_QUERIES)} categories\n\n")
            
            # Summary Table
            f.write("## Summary Table\n\n")
            f.write("| Rank | Model | Provider | Overall Score | Success Rate | Avg Response Time | Status | Recommendation |\n")
            f.write("|------|-------|----------|---------------|--------------|-------------------|--------|----------------|\n")
            
            for i, result in enumerate(sorted_results, 1):
                status_emoji = "✅" if result.test_status == "completed" else "❌"
                recommendation = self.get_recommendation(result.overall_score, result.success_rate)
                provider = next((m["provider"] for m in self.MODELS_TO_TEST if m["id"] == result.model_id), "Unknown")
                
                f.write(f"| {i} | {result.model_name} | {provider} | {result.overall_score:.1f}% | "
                       f"{result.success_rate:.1f}% | {result.avg_response_time:.0f}ms | {status_emoji} | {recommendation} |\n")
            
            # Category Performance
            f.write("\n## Category Performance\n\n")
            f.write("| Model | Simple Location | Coordinate Extraction | Multi-Location | Agricultural | Ambiguous |\n")
            f.write("|-------|-----------------|----------------------|----------------|--------------|------------|\n")
            
            for result in sorted_results:
                if result.test_status == "completed":
                    f.write(f"| {result.model_name} ")
                    for category in self.TEST_QUERIES.keys():
                        score = result.category_scores.get(category, 0)
                        f.write(f"| {score:.1f}% ")
                    f.write("|\n")
            
            # Detailed Results
            f.write("\n## Detailed Results\n\n")
            
            for result in sorted_results:
                f.write(f"### {result.model_name}\n\n")
                f.write(f"- **Model ID**: `{result.model_id}`\n")
                f.write(f"- **Status**: {result.test_status}\n")
                f.write(f"- **Overall Score**: {result.overall_score:.1f}%\n")
                f.write(f"- **Success Rate**: {result.success_rate:.1f}%\n")
                f.write(f"- **Average Response Time**: {result.avg_response_time:.0f}ms\n")
                f.write(f"- **Summary**: {result.summary}\n\n")
                
                if result.test_status == "completed":
                    # Show common issues
                    all_issues = []
                    for test in result.test_results:
                        all_issues.extend(test.issues)
                    
                    if all_issues:
                        issue_counts = {}
                        for issue in all_issues:
                            issue_counts[issue] = issue_counts.get(issue, 0) + 1
                        
                        f.write("**Common Issues**:\n")
                        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                            f.write(f"- {issue} ({count} occurrences)\n")
                        f.write("\n")
                    
                    # Category breakdown
                    f.write("**Category Scores**:\n")
                    for category, score in result.category_scores.items():
                        f.write(f"- {category}: {score:.1f}%\n")
                    f.write("\n")
            
            # Best Practices
            f.write("## Recommendations\n\n")
            f.write("### Production Ready Models (>85% score, >85% success rate)\n")
            prod_ready = [r for r in sorted_results if r.overall_score >= 85 and r.success_rate >= 85]
            if prod_ready:
                for result in prod_ready:
                    f.write(f"- **{result.model_name}**: {result.summary}\n")
            else:
                f.write("- No models met the production ready criteria\n")
            
            f.write("\n### Models Requiring Prompt Tuning (70-85% score)\n")
            needs_tuning = [r for r in sorted_results if 70 <= r.overall_score < 85]
            if needs_tuning:
                for result in needs_tuning:
                    f.write(f"- **{result.model_name}**: {result.summary}\n")
            
            f.write("\n### Not Recommended (<70% score)\n")
            not_recommended = [r for r in sorted_results if r.overall_score < 70]
            if not_recommended:
                for result in not_recommended:
                    f.write(f"- **{result.model_name}**: {result.summary}\n")
        
        print(f"\nReport saved to: {report_path}")
        
        # Also save raw results as JSON
        json_path = self.output_dir / f"model_compliance_results_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, "w") as f:
            json_data = []
            for result in self.results:
                json_data.append({
                    "model_id": result.model_id,
                    "model_name": result.model_name,
                    "description": result.description,
                    "test_status": result.test_status,
                    "overall_score": result.overall_score,
                    "success_rate": result.success_rate,
                    "avg_response_time": result.avg_response_time,
                    "category_scores": result.category_scores,
                    "summary": result.summary,
                    "test_count": len(result.test_results),
                    "successful_tests": sum(1 for t in result.test_results if t.success)
                })
            json.dump(json_data, f, indent=2)
        
        print(f"JSON results saved to: {json_path}")
        
        # Print top 5 models
        print("\nTop 5 Models by Overall Score:")
        for i, result in enumerate(sorted_results[:5], 1):
            print(f"{i}. {result.model_name}: {result.overall_score:.1f}% (Success Rate: {result.success_rate:.1f}%)")
    
    def get_recommendation(self, score: float, success_rate: float) -> str:
        """Get recommendation based on score and success rate"""
        if score >= 90 and success_rate >= 90:
            return "🟢 Production Ready"
        elif score >= 80 and success_rate >= 80:
            return "🟡 Use with Minor Tuning"
        elif score >= 70 and success_rate >= 70:
            return "🟠 Needs Prompt Engineering"
        elif score >= 60:
            return "🔴 Development Only"
        else:
            return "⛔ Not Recommended"


async def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AWS Bedrock models for structured output compliance")
    parser.add_argument("--models", nargs="+", help="Specific model IDs to test (tests all if not specified)")
    parser.add_argument("--output", default="test_results", help="Output directory for results")
    parser.add_argument("--quick", action="store_true", help="Quick test with fewer models")
    
    args = parser.parse_args()
    
    # Create tester
    tester = ModelComplianceTester(output_dir=args.output)
    
    # Quick test mode - only test a few key models
    if args.quick:
        quick_models = [
            "anthropic.claude-sonnet-4-20250514-v1:0",
            "anthropic.claude-3-7-sonnet-20250219-v1:0",
            "amazon.nova-premier-v1:0",
            "meta.llama3-3-70b-instruct-v1:0",
            "cohere.command-r-plus-v1:0"
        ]
        await tester.run_all_tests(models_to_test=quick_models)
    else:
        await tester.run_all_tests(models_to_test=args.models)


if __name__ == "__main__":
    asyncio.run(main())