#!/usr/bin/env python3
"""
Test different system prompts to see their effect on structured output compliance.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from weather_agent.mcp_agent import create_weather_agent
from weather_agent.models.structured_responses import WeatherQueryResponse


class PromptTester:
    """Test different system prompts and evaluate their effectiveness."""
    
    TEST_QUERIES = [
        "What's the weather in New York?",
        "Temperature at 40.7128, -74.0060",
        "Compare weather in London, Tokyo, and Sydney"
    ]
    
    PROMPT_FILES = [
        "system_prompt.txt",           # Current complex prompt
        "system_prompt_simple.txt",    # Simplified version
        "system_prompt_agriculture.txt" # Agriculture-agent-ecs style
    ]
    
    def __init__(self):
        self.results = {}
        
    async def test_prompt(self, prompt_file: str) -> Dict[str, Any]:
        """Test a single prompt file."""
        print(f"\n{'='*60}")
        print(f"Testing prompt: {prompt_file}")
        print(f"{'='*60}")
        
        try:
            # Create agent with specific prompt
            agent = await create_weather_agent(
                debug_logging=False,
                system_prompt_file=prompt_file
            )
            
            prompt_results = {
                "prompt_file": prompt_file,
                "model": agent.model_id,
                "queries": [],
                "overall_score": 0.0,
                "issues": []
            }
            
            # Test each query
            for query in self.TEST_QUERIES:
                print(f"\n📝 Query: {query}")
                
                try:
                    # Get structured response
                    response = await agent.query_structured(query)
                    
                    # Evaluate response
                    score, issues = self.evaluate_response(response, query)
                    
                    query_result = {
                        "query": query,
                        "score": score,
                        "issues": issues,
                        "locations_extracted": len(response.locations),
                        "location_details": [
                            {
                                "name": loc.name,
                                "lat": loc.latitude,
                                "lon": loc.longitude,
                                "confidence": loc.confidence
                            }
                            for loc in response.locations
                        ]
                    }
                    
                    prompt_results["queries"].append(query_result)
                    print(f"   Score: {score}% | Locations: {len(response.locations)}")
                    if issues:
                        print(f"   Issues: {', '.join(issues[:2])}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")
                    prompt_results["queries"].append({
                        "query": query,
                        "score": 0,
                        "error": str(e)
                    })
            
            # Calculate overall score
            scores = [q["score"] for q in prompt_results["queries"] if "score" in q]
            prompt_results["overall_score"] = sum(scores) / len(scores) if scores else 0
            
            # Collect all issues
            all_issues = []
            for q in prompt_results["queries"]:
                if "issues" in q:
                    all_issues.extend(q["issues"])
            prompt_results["issues"] = list(set(all_issues))
            
            return prompt_results
            
        except Exception as e:
            print(f"❌ Failed to test prompt: {e}")
            return {
                "prompt_file": prompt_file,
                "error": str(e),
                "overall_score": 0
            }
    
    def evaluate_response(self, response: WeatherQueryResponse, query: str) -> tuple[float, List[str]]:
        """Evaluate a structured response and return score and issues."""
        score = 100.0
        issues = []
        
        # Check locations
        if not response.locations:
            score -= 30
            issues.append("No locations extracted")
        else:
            for loc in response.locations:
                # Check for default/unknown locations
                if loc.name.lower() == "unknown":
                    score -= 10
                    issues.append(f"Invalid location name: '{loc.name}'")
                
                # Check coordinates
                if loc.latitude == 0.0 and loc.longitude == 0.0:
                    score -= 10
                    issues.append(f"Missing coordinates for {loc.name}")
                elif abs(loc.latitude) > 90 or abs(loc.longitude) > 180:
                    score -= 10
                    issues.append(f"Invalid coordinates for {loc.name}")
                
                # Check confidence
                if loc.confidence == 0.0:
                    score -= 5
                    issues.append(f"Low confidence (0.00) for {loc.name}")
                
                # Check timezone
                if not loc.timezone or loc.timezone == "UTC":
                    score -= 5
                    issues.append(f"Missing proper timezone for {loc.name}")
        
        # Check query type
        if response.query_type == "general" and any(word in query.lower() for word in ["weather", "temperature", "forecast"]):
            score -= 5
            issues.append("Query type should be more specific than 'general'")
        
        # Check summary
        if not response.summary or len(response.summary) < 10:
            score -= 10
            issues.append("Missing or inadequate summary")
        
        return max(0, score), issues
    
    async def run_tests(self):
        """Run all prompt tests."""
        print("🧪 Testing System Prompt Variations")
        print("=" * 60)
        
        for prompt_file in self.PROMPT_FILES:
            result = await self.test_prompt(prompt_file)
            self.results[prompt_file] = result
            
            # Brief delay between tests
            await asyncio.sleep(2)
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_path = Path(f"models_testing/test_results/prompt_test_results_{timestamp}.json")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate markdown report
        report = ["# System Prompt Test Results\n"]
        report.append(f"**Test Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Model**: {list(self.results.values())[0].get('model', 'Unknown')}\n")
        
        # Summary table
        report.append("\n## Summary\n")
        report.append("| Prompt File | Overall Score | Main Issues |")
        report.append("|-------------|---------------|-------------|")
        
        for prompt_file, result in self.results.items():
            if "error" in result:
                report.append(f"| {prompt_file} | ERROR | {result['error']} |")
            else:
                issues = ", ".join(result["issues"][:2]) if result["issues"] else "None"
                report.append(f"| {prompt_file} | {result['overall_score']:.1f}% | {issues} |")
        
        # Detailed results
        report.append("\n## Detailed Results\n")
        
        for prompt_file, result in self.results.items():
            report.append(f"\n### {prompt_file}\n")
            
            if "error" in result:
                report.append(f"❌ Error: {result['error']}\n")
                continue
            
            report.append(f"**Overall Score**: {result['overall_score']:.1f}%\n")
            
            if result["issues"]:
                report.append("\n**Common Issues**:")
                for issue in result["issues"][:5]:
                    report.append(f"- {issue}")
                report.append("")
            
            report.append("\n**Query Results**:\n")
            for query_result in result["queries"]:
                report.append(f"- Query: \"{query_result['query']}\"")
                if "error" in query_result:
                    report.append(f"  - Error: {query_result['error']}")
                else:
                    report.append(f"  - Score: {query_result['score']}%")
                    report.append(f"  - Locations extracted: {query_result['locations_extracted']}")
                    for loc in query_result["location_details"]:
                        report.append(f"    - {loc['name']}: ({loc['lat']}, {loc['lon']}) conf={loc['confidence']}")
        
        # Write markdown report
        md_path = Path(f"models_testing/test_results/prompt_test_report_{timestamp}.md")
        with open(md_path, 'w') as f:
            f.write("\n".join(report))
        
        # Also update structured-fixes.md
        self.update_structured_fixes(report)
        
        print(f"\n✅ Results saved to:")
        print(f"   - {json_path}")
        print(f"   - {md_path}")
    
    def update_structured_fixes(self, report: List[str]):
        """Update structured-fixes.md with test results."""
        fixes_path = Path("structured-fixes.md")
        
        if fixes_path.exists():
            content = fixes_path.read_text()
            
            # Find where to insert the new results
            marker = "## Prompt Testing Results"
            if marker in content:
                # Replace existing results
                parts = content.split(marker)
                new_content = parts[0] + marker + "\n\n" + "\n".join(report) + "\n"
                
                # Keep any content after the results if there was a second marker
                if "## " in parts[1]:
                    next_section = parts[1].find("## ")
                    new_content += parts[1][next_section:]
            else:
                # Add new section at the top after the comparison
                new_content = content.replace(
                    "### Proposed Solution:",
                    f"## Prompt Testing Results\n\n{chr(10).join(report)}\n\n### Proposed Solution:"
                )
            
            fixes_path.write_text(new_content)
            print(f"   - Updated structured-fixes.md")


async def main():
    """Run prompt tests."""
    # Ensure MCP servers are running
    print("⚠️  Make sure MCP servers are running on ports 8081-8083")
    print("   Run: ./scripts/start_servers.sh\n")
    
    tester = PromptTester()
    await tester.run_tests()


if __name__ == "__main__":
    asyncio.run(main())