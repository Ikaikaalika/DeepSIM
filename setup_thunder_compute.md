# Thunder Compute Integration Setup

This guide explains how to set up DeepSeek R1 on Thunder Compute platform for autonomous process engineering.

## Prerequisites

1. **Thunder Compute Account**: Sign up at [thunder.dev](https://thunder.dev)
2. **API Key**: Obtain your Thunder Compute API key from the dashboard
3. **DeepSeek R1 Access**: Ensure you have access to DeepSeek R1 models

## Setup Steps

### 1. Environment Configuration

Copy the environment template and configure your API keys:

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add your Thunder Compute API key:

```bash
THUNDER_API_KEY=tc_your_api_key_here_from_thunder_dashboard
DEEPSEEK_MODEL=deepseek-r1-distill-llama-70b
THUNDER_BASE_URL=https://api.thunder.dev
```

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Thunder CLI Setup (Optional)

If you have Thunder CLI installed, you can manage deployments:

```bash
# Login to Thunder
thunder auth login

# Deploy model (if needed)
thunder deploy --model deepseek-r1-distill-llama-70b --name deepsim-ai
```

### 4. Fine-tuning for Process Engineering

Create a fine-tuning dataset for chemical process engineering:

```python
# Process engineering training examples
training_data = [
    {
        "messages": [
            {"role": "system", "content": "You are an expert chemical process engineer..."},
            {"role": "user", "content": "Design a benzene-toluene separation process"},
            {"role": "assistant", "content": "I'll design a distillation-based separation..."}
        ]
    },
    # Add more training examples...
]
```

### 5. Model Fine-tuning Command

```bash
# Fine-tune DeepSeek R1 for process engineering
thunder fine-tune \
  --model deepseek-r1-distill-llama-70b \
  --dataset process_engineering_dataset.jsonl \
  --name deepsim-process-ai \
  --learning-rate 1e-4 \
  --epochs 3
```

## Usage

### 1. Start the Backend Server

```bash
cd backend
python main.py
```

The server will initialize the AI engine with Thunder Compute integration.

### 2. API Endpoints

The following AI endpoints are available:

- `POST /ai/chat` - Main AI chat interface
- `GET /health` - Check AI service status
- `POST /llm/chat` - Legacy endpoint (redirects to /ai/chat)

### 3. Example API Usage

```javascript
// Frontend integration
const response = await fetch('http://localhost:8000/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: "Design a reactor system with heat integration",
        flowsheet_id: "optional-flowsheet-id",
        context: { current_units: 0, unit_types: [] }
    })
});

const aiResponse = await response.json();
// aiResponse.response contains the AI's message
// aiResponse.actions contains executable actions
// aiResponse.confidence shows model confidence
```

## AI Capabilities

### Autonomous Process Design
- **Input**: "Design a benzene-toluene separation process"
- **Output**: Complete flowsheet with distillation column, utilities, optimized parameters

### Process Optimization
- **Input**: "Optimize current flowsheet for energy efficiency"
- **Output**: Parameter adjustments, heat integration suggestions

### Autonomous Testing
- **Input**: "Run comprehensive testing on this process"
- **Output**: Sensitivity analysis, robustness testing, performance validation

## Process Engineering Knowledge Base

The AI is pre-trained with:

- **Unit Operations**: Distillation, reactors, heat exchangers, separations
- **Thermodynamics**: Peng-Robinson, UNIFAC, NRTL, Wilson equations
- **Process Design**: MESH equations, flash calculations, energy balances
- **Industrial Practices**: Safety standards, economic optimization
- **Simulation Methods**: Rigorous modeling, convergence algorithms

## Monitoring and Debugging

### Health Check
```bash
curl http://localhost:8000/health
```

### Log Monitoring
```bash
tail -f logs/deepsim.log
```

### AI Response Analysis
Check the response for:
- `confidence`: Model confidence (0-1)
- `reasoning`: AI's decision-making process
- `suggested_followups`: Next recommended actions

## Fallback Mode

If Thunder Compute is unavailable, the system automatically falls back to:
1. Local AI processing (rule-based)
2. OpenAI GPT-4 (if configured)
3. Anthropic Claude (if configured)

## Production Deployment

For production deployment:

1. **Environment Variables**: Set all required environment variables
2. **API Limits**: Configure rate limiting and quotas
3. **Monitoring**: Set up health checks and alerting
4. **Scaling**: Use Thunder's auto-scaling features
5. **Security**: Implement proper authentication and authorization

## Support

For issues with Thunder Compute integration:
- Thunder Compute Documentation: [docs.thunder.dev](https://docs.thunder.dev)
- DeepSeek Model Documentation: Check Thunder model catalog
- DeepSim Issues: [GitHub Issues](https://github.com/your-repo/DeepSIM/issues)

## Cost Optimization

Thunder Compute pricing tips:
- Use batch processing for multiple requests
- Implement request caching for repeated queries
- Monitor token usage and optimize prompt lengths
- Use streaming responses for real-time chat