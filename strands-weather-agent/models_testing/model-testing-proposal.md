# Model Testing Proposal: Structured Output Compliance Across AWS Bedrock Models

## Executive Summary

This proposal outlines a systematic approach to test structured output compliance across different AWS Bedrock foundation models. The goal is to identify which models best support the AWS Strands structured output pattern for the Weather Agent application.

## Testing Objectives

1. **Evaluate structured output compliance** - Which models correctly populate all required fields in `WeatherQueryResponse`
2. **Assess geographic intelligence** - How well models extract location coordinates using built-in knowledge
3. **Measure response quality** - Completeness, accuracy, and formatting of structured responses
4. **Document model-specific quirks** - Identify any special handling needed per model
5. **Performance benchmarking** - Response time and token usage comparison

## Test Methodology

### 1. Test Query Set

```python
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
        "Frost risk for crops in Minneapolis"
    ],
    "ambiguous": [
        "Weather in Springfield",
        "Temperature in Washington"
    ]
}
```

### 2. Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Field Completion | 40% | All required fields populated (summary, locations, query_type) |
| Coordinate Accuracy | 30% | Correct lat/lon within 0.1 degrees |
| Response Validity | 20% | Passes Pydantic validation without errors |
| Geographic Metadata | 10% | Includes timezone, country code, confidence scores |

### 3. Testing Script

```python
# test_model_compliance.py
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
from weather_agent.mcp_agent import MCPWeatherAgent
from models.structured_responses import WeatherQueryResponse

class ModelComplianceTester:
    """Test structured output compliance across models."""
    
    def __init__(self):
        self.results = []
        self.models_to_test = [
            # Anthropic Claude Models
            ("anthropic.claude-3-7-sonnet-20250219-v1:0", "Claude 3.7 Sonnet", "Latest Claude, best compliance expected"),
            ("anthropic.claude-3-5-sonnet-20241022-v2:0", "Claude 3.5 Sonnet v2", "Strong structured output support"),
            ("anthropic.claude-3-5-sonnet-20240620-v1:0", "Claude 3.5 Sonnet v1", "Proven reliable"),
            ("anthropic.claude-3-5-haiku-20241022-v1:0", "Claude 3.5 Haiku", "Fast but may struggle with complex output"),
            ("anthropic.claude-3-opus-20240229-v1:0", "Claude 3 Opus", "Older but capable"),
            
            # Amazon Nova Models
            ("amazon.nova-premier-v1:0", "Nova Premier", "Amazon's flagship model"),
            ("amazon.nova-pro-v1:0", "Nova Pro", "Balanced Nova model"),
            ("amazon.nova-lite-v1:0", "Nova Lite", "Fast but limited"),
            
            # Meta Llama Models
            ("meta.llama3-3-70b-instruct-v1:0", "Llama 3.3 70B", "Latest open-source"),
            ("meta.llama3-1-405b-instruct-v1:0", "Llama 3.1 405B", "Largest Llama"),
            
            # Other Models
            ("cohere.command-r-plus-v1:0", "Command R+", "Strong factual responses"),
            ("mistral.mistral-large-2407-v1:0", "Mistral Large", "European alternative")
        ]
    
    async def test_model(self, model_id: str, model_name: str, description: str) -> Dict[str, Any]:
        """Test a single model for structured output compliance."""
        print(f"\n{'='*60}")
        print(f"Testing: {model_name}")
        print(f"Model ID: {model_id}")
        print(f"Description: {description}")
        print('='*60)
        
        # Initialize agent with specific model
        agent = MCPWeatherAgent(
            bedrock_model_id=model_id,
            debug_logging=False
        )
        
        model_results = {
            "model_id": model_id,
            "model_name": model_name,
            "description": description,
            "test_results": {},
            "overall_score": 0,
            "summary": ""
        }
        
        # Test each query category
        for category, queries in TEST_QUERIES.items():
            category_scores = []
            
            for query in queries:
                try:
                    print(f"\nTesting: {query}")
                    start_time = datetime.now()
                    
                    # Get structured response
                    response = await agent.query_structured(query)
                    
                    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                    
                    # Evaluate response
                    score, details = self.evaluate_response(response, query, elapsed_ms)
                    category_scores.append(score)
                    
                    print(f"Score: {score:.2f}/100")
                    if score < 100:
                        print(f"Issues: {details.get('issues', [])}")
                
                except Exception as e:
                    print(f"ERROR: {str(e)}")
                    category_scores.append(0)
            
            # Average score for category
            model_results["test_results"][category] = sum(category_scores) / len(category_scores)
        
        # Calculate overall score
        model_results["overall_score"] = sum(model_results["test_results"].values()) / len(model_results["test_results"])
        
        # Generate summary
        model_results["summary"] = self.generate_model_summary(model_results)
        
        return model_results
    
    def evaluate_response(self, response: WeatherQueryResponse, query: str, elapsed_ms: float) -> tuple[float, Dict]:
        """Evaluate a structured response for compliance."""
        score = 100.0
        issues = []
        details = {"elapsed_ms": elapsed_ms}
        
        # Check required fields
        if not response.summary or response.summary == "":
            score -= 20
            issues.append("Missing summary field")
        
        if not response.locations:
            score -= 20
            issues.append("No locations extracted")
        else:
            # Check location quality
            for loc in response.locations:
                if loc.name == "Unknown" or not loc.name:
                    score -= 10
                    issues.append(f"Invalid location name: {loc.name}")
                
                if loc.latitude == 0 and loc.longitude == 0:
                    score -= 15
                    issues.append(f"Invalid coordinates for {loc.name}")
                
                if not hasattr(loc, 'timezone') or not loc.timezone:
                    score -= 5
                    issues.append(f"Missing timezone for {loc.name}")
        
        if not response.query_type or response.query_type == "unknown":
            score -= 10
            issues.append("Invalid query type")
        
        # Performance penalty for slow responses
        if elapsed_ms > 5000:
            score -= 5
            issues.append(f"Slow response: {elapsed_ms:.0f}ms")
        
        details["issues"] = issues
        return max(0, score), details
    
    def generate_model_summary(self, results: Dict) -> str:
        """Generate a summary of model performance."""
        score = results["overall_score"]
        
        if score >= 90:
            return "Excellent structured output compliance. Ready for production use."
        elif score >= 70:
            return "Good compliance with minor issues. May need prompt adjustments."
        elif score >= 50:
            return "Moderate compliance. Requires prompt engineering or fallback handling."
        else:
            return "Poor structured output support. Not recommended for this use case."
    
    async def run_all_tests(self):
        """Run tests on all models."""
        print("Starting Model Compliance Testing")
        print(f"Testing {len(self.models_to_test)} models across {len(TEST_QUERIES)} query categories")
        
        for model_id, model_name, description in self.models_to_test:
            try:
                result = await self.test_model(model_id, model_name, description)
                self.results.append(result)
            except Exception as e:
                print(f"Failed to test {model_name}: {str(e)}")
                self.results.append({
                    "model_id": model_id,
                    "model_name": model_name,
                    "description": description,
                    "overall_score": 0,
                    "summary": f"Failed to test: {str(e)}"
                })
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report."""
        # Sort by overall score
        sorted_results = sorted(self.results, key=lambda x: x["overall_score"], reverse=True)
        
        # Create summary table
        print("\n" + "="*80)
        print("MODEL COMPLIANCE TEST RESULTS")
        print("="*80)
        
        # Generate markdown table
        with open("model-test-results.md", "w") as f:
            f.write("# Model Compliance Test Results\n\n")
            f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary Table\n\n")
            f.write("| Rank | Model | Overall Score | Compliance Level | Recommendation |\n")
            f.write("|------|-------|---------------|------------------|----------------|\n")
            
            for i, result in enumerate(sorted_results, 1):
                compliance = self.get_compliance_level(result["overall_score"])
                recommendation = self.get_recommendation(result["overall_score"])
                
                f.write(f"| {i} | {result['model_name']} | {result['overall_score']:.1f}% | {compliance} | {recommendation} |\n")
            
            f.write("\n## Detailed Results\n\n")
            
            for result in sorted_results:
                f.write(f"### {result['model_name']}\n")
                f.write(f"- **Model ID**: `{result['model_id']}`\n")
                f.write(f"- **Overall Score**: {result['overall_score']:.1f}%\n")
                f.write(f"- **Summary**: {result['summary']}\n")
                f.write(f"- **Category Scores**:\n")
                for category, score in result.get("test_results", {}).items():
                    f.write(f"  - {category}: {score:.1f}%\n")
                f.write("\n")
    
    def get_compliance_level(self, score: float) -> str:
        """Get compliance level from score."""
        if score >= 90:
            return "✅ Excellent"
        elif score >= 70:
            return "🟨 Good"
        elif score >= 50:
            return "🟧 Moderate"
        else:
            return "❌ Poor"
    
    def get_recommendation(self, score: float) -> str:
        """Get recommendation based on score."""
        if score >= 90:
            return "Production Ready"
        elif score >= 70:
            return "Use with Prompt Tuning"
        elif score >= 50:
            return "Development Only"
        else:
            return "Not Recommended"

# Main execution
if __name__ == "__main__":
    tester = ModelComplianceTester()
    asyncio.run(tester.run_all_tests())
```

## Testing Schedule

### Phase 1: Baseline Testing (Day 1)
1. Test current model (Nova Premier) to establish baseline
2. Test Claude 3.7 Sonnet as gold standard
3. Document initial findings

### Phase 2: Comprehensive Testing (Day 2-3)
1. Test all Anthropic models
2. Test all Amazon Nova models
3. Test Meta Llama models
4. Test Cohere and Mistral models

### Phase 3: Analysis and Optimization (Day 4)
1. Analyze results and identify patterns
2. Create model-specific prompt adjustments
3. Re-test failing models with optimized prompts
4. Document best practices per model

## Expected Outcomes

### Model Performance Matrix

| Model Category | Expected Performance | Key Considerations |
|----------------|---------------------|-------------------|
| Claude 3.7/3.5 | 90-100% compliance | Best structured output support |
| Nova Premier/Pro | 70-85% compliance | Good with prompt tuning |
| Llama 3.x | 60-75% compliance | May need explicit examples |
| Claude Haiku | 70-80% compliance | Fast but less capable |
| Cohere Command | 65-80% compliance | Strong factual accuracy |
| Mistral | 60-75% compliance | European data advantages |

### Common Issues by Model Type

1. **Anthropic Models**: Generally excellent, may over-explain
2. **Nova Models**: Good but may need clearer field instructions
3. **Llama Models**: Tendency to be verbose, need strict formatting
4. **Cohere Models**: Strong facts but may miss metadata fields
5. **Mistral Models**: Good reasoning but formatting inconsistencies

## Deliverables

1. **Model Test Results** (`model-test-results.md`)
   - Comprehensive scoring table
   - Detailed findings per model
   - Production readiness assessment

2. **Model-Specific Configurations** (`model-configs.json`)
   - Optimal prompts per model
   - Temperature settings
   - Retry strategies

3. **Best Practices Guide** (`model-best-practices.md`)
   - Model selection criteria
   - Fallback strategies
   - Cost/performance tradeoffs

4. **Updated Documentation**
   - Update CLAUDE.md with model recommendations
   - Update .env with test results
   - Create model switching guide

## Implementation Code

The testing framework will be implemented as a standalone script that:
1. Loads each model configuration
2. Runs standardized test queries
3. Evaluates responses automatically
4. Generates comprehensive reports
5. Saves results for analysis

## Success Criteria

1. **Identify 3+ production-ready models** with >85% compliance
2. **Document workarounds** for models with 70-85% compliance
3. **Create switching strategy** for model failover
4. **Establish baseline metrics** for future model additions

## Next Steps

1. Review and approve testing methodology
2. Set up test environment with proper AWS credentials
3. Run initial baseline tests
4. Execute full test suite
5. Analyze results and create recommendations
6. Implement model-specific optimizations
7. Document findings and best practices

This systematic approach will ensure we identify the best models for structured output compliance and create a robust multi-model strategy for the Weather Agent application.