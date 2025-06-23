# AWS Bedrock Model Compliance Test Report

**Test Date**: 2025-06-23 14:37:57
**Duration**: 12.9 seconds
**Models Tested**: 5
**Total Queries**: 12 queries across 5 categories

## Summary Table

| Rank | Model | Provider | Overall Score | Success Rate | Avg Response Time | Status | Recommendation |
|------|-------|----------|---------------|--------------|-------------------|--------|----------------|
| 1 | Claude Sonnet 4 | Anthropic | 70.0% | 100.0% | 287ms | ✅ | 🟠 Needs Prompt Engineering |
| 2 | Claude 3.7 Sonnet | Anthropic | 70.0% | 100.0% | 172ms | ✅ | 🟠 Needs Prompt Engineering |
| 3 | Nova Premier | Amazon | 70.0% | 100.0% | 176ms | ✅ | 🟠 Needs Prompt Engineering |
| 4 | Llama 3.3 70B | Meta | 70.0% | 100.0% | 213ms | ✅ | 🟠 Needs Prompt Engineering |
| 5 | Command R+ | Cohere | 70.0% | 100.0% | 213ms | ✅ | 🟠 Needs Prompt Engineering |

## Category Performance

| Model | Simple Location | Coordinate Extraction | Multi-Location | Agricultural | Ambiguous |
|-------|-----------------|----------------------|----------------|--------------|------------|
| Claude Sonnet 4 | 70.0% | 70.0% | 70.0% | 70.0% | 70.0% |
| Claude 3.7 Sonnet | 70.0% | 70.0% | 70.0% | 70.0% | 70.0% |
| Nova Premier | 70.0% | 70.0% | 70.0% | 70.0% | 70.0% |
| Llama 3.3 70B | 70.0% | 70.0% | 70.0% | 70.0% | 70.0% |
| Command R+ | 70.0% | 70.0% | 70.0% | 70.0% | 70.0% |

## Detailed Results

### Claude Sonnet 4

- **Model ID**: `anthropic.claude-sonnet-4-20250514-v1:0`
- **Status**: completed
- **Overall Score**: 70.0%
- **Success Rate**: 100.0%
- **Average Response Time**: 287ms
- **Summary**: Good compliance with some issues. Prompt engineering needed.

**Common Issues**:
- Invalid location name: 'Unknown' (12 occurrences)
- Missing coordinates for Unknown (12 occurrences)
- Low confidence (0.00) for Unknown (12 occurrences)

**Category Scores**:
- simple_location: 70.0%
- coordinate_extraction: 70.0%
- multi_location: 70.0%
- agricultural: 70.0%
- ambiguous: 70.0%

### Claude 3.7 Sonnet

- **Model ID**: `anthropic.claude-3-7-sonnet-20250219-v1:0`
- **Status**: completed
- **Overall Score**: 70.0%
- **Success Rate**: 100.0%
- **Average Response Time**: 172ms
- **Summary**: Good compliance with some issues. Prompt engineering needed.

**Common Issues**:
- Invalid location name: 'Unknown' (12 occurrences)
- Missing coordinates for Unknown (12 occurrences)
- Low confidence (0.00) for Unknown (12 occurrences)

**Category Scores**:
- simple_location: 70.0%
- coordinate_extraction: 70.0%
- multi_location: 70.0%
- agricultural: 70.0%
- ambiguous: 70.0%

### Nova Premier

- **Model ID**: `amazon.nova-premier-v1:0`
- **Status**: completed
- **Overall Score**: 70.0%
- **Success Rate**: 100.0%
- **Average Response Time**: 176ms
- **Summary**: Good compliance with some issues. Prompt engineering needed.

**Common Issues**:
- Invalid location name: 'Unknown' (12 occurrences)
- Missing coordinates for Unknown (12 occurrences)
- Low confidence (0.00) for Unknown (12 occurrences)

**Category Scores**:
- simple_location: 70.0%
- coordinate_extraction: 70.0%
- multi_location: 70.0%
- agricultural: 70.0%
- ambiguous: 70.0%

### Llama 3.3 70B

- **Model ID**: `meta.llama3-3-70b-instruct-v1:0`
- **Status**: completed
- **Overall Score**: 70.0%
- **Success Rate**: 100.0%
- **Average Response Time**: 213ms
- **Summary**: Good compliance with some issues. Prompt engineering needed.

**Common Issues**:
- Invalid location name: 'Unknown' (12 occurrences)
- Missing coordinates for Unknown (12 occurrences)
- Low confidence (0.00) for Unknown (12 occurrences)

**Category Scores**:
- simple_location: 70.0%
- coordinate_extraction: 70.0%
- multi_location: 70.0%
- agricultural: 70.0%
- ambiguous: 70.0%

### Command R+

- **Model ID**: `cohere.command-r-plus-v1:0`
- **Status**: completed
- **Overall Score**: 70.0%
- **Success Rate**: 100.0%
- **Average Response Time**: 213ms
- **Summary**: Good compliance with some issues. Prompt engineering needed.

**Common Issues**:
- Invalid location name: 'Unknown' (12 occurrences)
- Missing coordinates for Unknown (12 occurrences)
- Low confidence (0.00) for Unknown (12 occurrences)

**Category Scores**:
- simple_location: 70.0%
- coordinate_extraction: 70.0%
- multi_location: 70.0%
- agricultural: 70.0%
- ambiguous: 70.0%

## Recommendations

### Production Ready Models (>85% score, >85% success rate)
- No models met the production ready criteria

### Models Requiring Prompt Tuning (70-85% score)
- **Claude Sonnet 4**: Good compliance with some issues. Prompt engineering needed.
- **Claude 3.7 Sonnet**: Good compliance with some issues. Prompt engineering needed.
- **Nova Premier**: Good compliance with some issues. Prompt engineering needed.
- **Llama 3.3 70B**: Good compliance with some issues. Prompt engineering needed.
- **Command R+**: Good compliance with some issues. Prompt engineering needed.

### Not Recommended (<70% score)
