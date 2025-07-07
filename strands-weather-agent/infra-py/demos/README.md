# AWS Strands Weather Agent Demos

This directory contains comprehensive demonstration scripts showcasing the capabilities of the AWS Strands Weather Agent, including multi-turn conversations, telemetry integration, and performance metrics.

## 🚀 Quick Start

Run all demos in sequence:
```bash
python infra-py/demos/run_all_demos.py
```

## 📂 Demo Scripts

### 1. `multi-turn-demo.py` - Multi-Turn Conversation Demo
Demonstrates stateful conversations with session management:
- Session persistence across queries
- Context maintenance for follow-up questions
- Invalid session handling
- Structured output with sessions
- Performance comparisons between initial and follow-up queries
- Comprehensive metrics summary

**Run individually:**
```bash
python infra-py/demos/multi-turn-demo.py
```

### 2. `demo_telemetry.py` - Telemetry Integration Demo
Showcases Langfuse telemetry integration:
- Real-time trace recording
- Token usage tracking
- Latency measurements
- Cost estimation
- Session-based telemetry grouping

**Run individually:**
```bash
python infra-py/demos/demo_telemetry.py
```

### 3. `performance_benchmark.py` - Performance Benchmark Demo
Comprehensive performance testing including:
- Latency measurements across query types
- Sustained throughput testing
- Concurrent client handling
- Stress testing to find limits
- Cost analysis and recommendations

**Run individually:**
```bash
python infra-py/demos/performance_benchmark.py
```

### 4. `run_all_demos.py` - Complete Demo Suite
Runs all demos in sequence with:
- Environment validation
- Sequential demo execution
- Comprehensive results summary
- Next steps guidance
- Optional performance benchmarking

## 📊 Metrics and Analytics

All demos provide detailed metrics including:

### Query Statistics
- Total queries executed
- Successful vs failed queries
- Unique session count

### Token Usage
- Total tokens consumed
- Input/output token breakdown
- Average tokens per query
- Token-based cost estimation

### Performance Metrics
- Total processing time
- Average latency per query
- Overall throughput (tokens/second)
- Agent execution cycles
- Model identification

### Cost Analysis
- Estimated input costs
- Estimated output costs
- Total estimated costs
- Model-specific pricing

## 🔧 Prerequisites

1. **Environment Setup:**
   ```bash
   # Copy and configure environment variables
   cp cloud.env.example cloud.env
   # Edit cloud.env with your settings
   ```

2. **AWS Credentials:**
   - Configure AWS CLI: `aws configure`
   - Or use environment variables
   - Ensure Bedrock access is enabled

3. **Service Running:**
   - Local: `python main.py`
   - Docker: `./scripts/start_docker.sh`
   - AWS: `python infra-py/deploy.py all`

## 🌟 Key Features Demonstrated

### Multi-Turn Conversations
- **Temporal Context**: "What's the weather tomorrow?" after asking about today
- **Location Memory**: Follow-up questions about previously mentioned cities
- **Agricultural Context**: Consecutive queries about different crops in same location

### Session Management
- Automatic session creation
- Session info retrieval
- Session deletion
- Invalid session handling
- Session expiration (60 minutes)

### Telemetry Integration
- Real-time trace recording
- Tool call tracking
- Latency breakdowns
- Token usage analytics
- Cost tracking

### Performance Analysis
- API round-trip times
- Model processing times
- Token efficiency in follow-ups
- Throughput measurements

## 📈 Example Output

```
📊 OVERALL METRICS SUMMARY
==========================

Query Statistics:
  Total Queries: 15
  Successful Queries: 15
  Unique Sessions: 3

Token Usage:
  Total Tokens: 4,523
  Input Tokens: 2,145
  Output Tokens: 2,378
  Average per Query: 301 tokens (143 in, 158 out)

Performance:
  Total Processing Time: 23.5s
  Average Latency: 1.57s per query
  Overall Throughput: 192 tokens/second
  Total Agent Cycles: 15
  Model: anthropic.claude-3-5-sonnet-20241022-v2:0

Cost Estimation:
  Estimated Input Cost: $0.0064
  Estimated Output Cost: $0.0357
  Estimated Total Cost: $0.0421
  (Note: Actual costs depend on your AWS pricing tier)
```

## 🔍 Troubleshooting

### API Not Accessible
```bash
# Check if service is running
curl http://localhost:7777/health

# For Docker deployment
docker ps | grep weather-agent

# For AWS deployment
python infra-py/deploy.py status
```

### Missing Dependencies
```bash
# Install required packages
pip install requests boto3 colorama python-dotenv
```

### AWS Credentials Issues
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

## 📚 Next Steps

After running the demos:

1. **Explore the API**: Visit http://localhost:7777/docs
2. **Check Telemetry**: View traces in your Langfuse dashboard
3. **Run Custom Queries**: Use the API directly with your own questions
4. **Deploy to Production**: Use `infra-py/deploy.py` for AWS deployment

## 🛠️ Advanced Usage

### Custom Session Testing
```python
# Test with specific session ID
API_URL=http://your-alb-url.com python infra-py/demos/multi-turn-demo.py
```

### Telemetry Configuration
```bash
# Enable telemetry
export LANGFUSE_PUBLIC_KEY=your_key
export LANGFUSE_SECRET_KEY=your_secret
export LANGFUSE_HOST=https://us.cloud.langfuse.com
```

### Performance Testing
```bash
# Run multiple iterations
for i in {1..5}; do
    python infra-py/demos/multi-turn-demo.py
done
```

## 📝 Notes

- Demos automatically detect deployed services via CloudFormation
- Metrics are accumulated across all queries in a demo run
- Cost estimates are based on typical AWS Bedrock pricing
- Session timeout is set to 60 minutes by default
- All demos support both local and deployed environments