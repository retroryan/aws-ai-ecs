# Model Compliance Testing

This directory contains scripts and tools for testing AWS Bedrock model compliance with structured output requirements for the Weather Agent.

## Files

- `test_model_compliance.py` - Main testing script that evaluates models
- `run_model_tests.sh` - Runner script with proper environment setup
- `model-testing-proposal.md` - Detailed testing methodology and expected outcomes
- `test_results/` - Directory where test results are saved (created on first run)

## Usage

Run from this directory:

```bash
# Test all models (takes 20-30 minutes)
./run_model_tests.sh

# Quick test with key models only (5-10 minutes)
./run_model_tests.sh --quick

# Test specific models
./run_model_tests.sh --models "anthropic.claude-sonnet-4-20250514-v1:0" "amazon.nova-premier-v1:0"
```

## Test Categories

1. **Simple Location** - Basic weather queries
2. **Coordinate Extraction** - Tests geographic intelligence
3. **Multi-Location** - Complex queries with multiple locations
4. **Agricultural** - Domain-specific queries
5. **Ambiguous** - Tests clarification handling

## Output

Results are saved in `test_results/` with:
- Markdown report with rankings and recommendations
- JSON file with raw test data
- Timestamp in filename for tracking multiple runs

## Models Tested

- Anthropic Claude models (Sonnet 4, 3.7, 3.5, Haiku, Opus)
- Amazon Nova models (Premier, Pro, Lite, Micro)
- Meta Llama models (3.3, 3.2, 3.1)
- Cohere models (Command R+, Command R)
- Mistral models (Large, Mixtral)