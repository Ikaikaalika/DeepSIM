#!/bin/bash
# DeepSim Thunder Compute Deployment Script

echo "🌩️  Deploying DeepSim to Thunder Compute..."

# Check Thunder CLI is available
if ! command -v thunder &> /dev/null; then
    echo "❌ Thunder CLI not found. Please install it first."
    exit 1
fi

# Check if logged in
if ! thunder whoami &> /dev/null; then
    echo "❌ Not logged into Thunder. Please run: thunder login"
    exit 1
fi

echo "✅ Thunder CLI ready"

# Create deployment directory
mkdir -p thunder_deploy
cd thunder_deploy

# Create model configuration
cat > model_config.yaml << 'EOF'
name: deepsim-deepseek-r1
base_model: deepseek-ai/deepseek-r1-7b
model_type: causal_lm
task_type: text-generation

# LoRA configuration
adapter_config:
  peft_type: LORA
  r: 16
  lora_alpha: 32
  target_modules: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
  lora_dropout: 0.1
  bias: "none"

# Inference configuration
inference:
  max_tokens: 2048
  temperature: 0.1
  top_p: 0.9
  stop_sequences: ["<|endoftext|>"]

# Quantization for efficiency
quantization:
  load_in_4bit: true
  bnb_4bit_quant_type: nf4
  bnb_4bit_compute_dtype: bfloat16

# Scaling configuration
scaling:
  min_replicas: 1
  max_replicas: 3
  target_gpu_utilization: 70
EOF

echo "📝 Created model configuration"

# Create inference endpoint configuration
cat > inference_config.yaml << 'EOF'
name: deepsim-inference
model: deepsim-deepseek-r1
gpu_type: A100-40GB
replicas: 1

endpoints:
  - path: /chat/completions
    method: POST
    description: "OpenAI-compatible chat completions endpoint"
  
  - path: /health
    method: GET
    description: "Health check endpoint"

environment:
  CUDA_VISIBLE_DEVICES: "0"
  TRANSFORMERS_CACHE: "/cache"
  HF_HOME: "/cache"

# Request/response format
input_schema:
  type: object
  properties:
    messages:
      type: array
      items:
        type: object
        properties:
          role:
            type: string
            enum: ["system", "user", "assistant"]
          content:
            type: string
    max_tokens:
      type: integer
      default: 2048
    temperature:
      type: number
      default: 0.1

output_schema:
  type: object
  properties:
    choices:
      type: array
      items:
        type: object
        properties:
          message:
            type: object
            properties:
              role:
                type: string
              content:
                type: string
EOF

echo "🔧 Created inference configuration"

# Deploy the model if training data exists
if [ -f "../llm_finetune/dataset.jsonl" ]; then
    echo "🚀 Starting model training on Thunder..."
    
    # Upload training script and data
    thunder upload ../llm_finetune/train_deepseek_thunder.py
    thunder upload ../llm_finetune/dataset.jsonl
    thunder upload ../llm_finetune/training_config.json
    thunder upload ../llm_finetune/requirements.txt
    
    # Start training job
    thunder train \
        --config model_config.yaml \
        --script train_deepseek_thunder.py \
        --data dataset.jsonl \
        --requirements requirements.txt \
        --gpu A100-40GB \
        --name deepsim-training
    
    echo "⏳ Training job submitted. Monitor with: thunder jobs list"
    echo "📊 View training progress: thunder logs deepsim-training"
    
    # Wait for training completion (optional)
    read -p "🤔 Wait for training to complete before deploying inference? (y/n): " wait_training
    
    if [ "$wait_training" = "y" ]; then
        echo "⏳ Waiting for training to complete..."
        thunder wait deepsim-training
        echo "✅ Training completed!"
    fi
else
    echo "⚠️  No training data found. Using base model..."
fi

# Deploy inference endpoint
echo "🚀 Deploying inference endpoint..."

thunder deploy \
    --config inference_config.yaml \
    --model deepsim-deepseek-r1 \
    --name deepsim-inference \
    --gpu A100-40GB \
    --replicas 1

echo "⏳ Deployment in progress..."

# Wait for deployment
thunder wait deepsim-inference

# Get endpoint URL
ENDPOINT_URL=$(thunder info deepsim-inference --format json | jq -r '.endpoint_url')

echo "✅ Deployment complete!"
echo "🌐 Inference endpoint: $ENDPOINT_URL"
echo "🔑 API Key: $(thunder auth token)"

# Create environment file for backend
cat > ../backend/.env << EOF
THUNDER_ENDPOINT=$ENDPOINT_URL
THUNDER_API_KEY=$(thunder auth token)
DATABASE_URL=sqlite:///data/database.sqlite
API_HOST=0.0.0.0
API_PORT=8000
EOF

echo "💾 Created backend/.env with Thunder credentials"

# Test the endpoint
echo "🧪 Testing inference endpoint..."

curl -X POST "$ENDPOINT_URL/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $(thunder auth token)" \
    -d '{
        "messages": [
            {
                "role": "system",
                "content": "You are an expert chemical process engineer. Help design chemical processes."
            },
            {
                "role": "user", 
                "content": "Create a simple methanol production flowsheet"
            }
        ],
        "max_tokens": 1000,
        "temperature": 0.1
    }' | jq '.'

echo ""
echo "🎉 Thunder Compute deployment complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update your application to use the new endpoint"
echo "   2. Deploy your backend with the Thunder credentials"
echo "   3. Test the full integration"
echo ""
echo "📊 Monitor your deployment:"
echo "   thunder status deepsim-inference"
echo "   thunder logs deepsim-inference"
echo "   thunder metrics deepsim-inference"

cd ..
EOF