"""
DeepSeek R1 Fine-tuning Script for Thunder Compute
Trains DeepSeek R1 model for chemical process simulation tasks using LoRA/QLoRA
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import argparse
from pathlib import Path

import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    PeftConfig,
    PeftModel
)
from datasets import Dataset, load_dataset
import wandb

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeepSeekTrainer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get('model_name', 'deepseek-ai/deepseek-r1-7b')
        self.output_dir = config.get('output_dir', './deepsim_deepseek_lora')
        self.dataset_path = config.get('dataset_path', './dataset.jsonl')
        
        # Thunder Compute configuration
        self.thunder_endpoint = os.getenv('THUNDER_ENDPOINT')
        self.thunder_api_key = os.getenv('THUNDER_API_KEY')
        
        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            padding_side="left"
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def setup_model(self) -> torch.nn.Module:
        """Setup model with quantization and LoRA configuration"""
        
        # BitsAndBytesConfig for 4-bit quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True
        )
        
        # Load model with quantization
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        
        # Prepare model for training
        model = prepare_model_for_kbit_training(model)
        
        # LoRA configuration
        lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            ],
            lora_dropout=0.1,
            bias="none",
            task_type="CAUSAL_LM"
        )
        
        # Apply LoRA
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()
        
        return model
    
    def load_dataset(self) -> Dataset:
        """Load and preprocess training dataset"""
        
        if not Path(self.dataset_path).exists():
            logger.warning(f"Dataset not found at {self.dataset_path}, creating sample dataset")
            self.create_sample_dataset()
        
        # Load JSONL dataset
        with open(self.dataset_path, 'r') as f:
            data = [json.loads(line) for line in f]
        
        # Convert to Hugging Face Dataset
        dataset = Dataset.from_list(data)
        
        # Tokenize dataset
        def tokenize_function(examples):
            # Create instruction-following format
            texts = []
            for i in range(len(examples['instruction'])):
                text = f"### Instruction:\n{examples['instruction'][i]}\n\n### Response:\n{examples['response'][i]}<|endoftext|>"
                texts.append(text)
            
            return self.tokenizer(
                texts,
                truncation=True,
                padding=True,
                max_length=self.config.get('max_length', 2048),
                return_tensors="pt"
            )
        
        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names
        )
        
        return tokenized_dataset
    
    def create_sample_dataset(self):
        """Create sample training dataset for chemical process simulation"""
        
        sample_data = [
            {
                "instruction": "Create a methanol production flowsheet with a reactor and distillation column",
                "response": json.dumps({
                    "action": "create_flowsheet",
                    "units": [
                        {
                            "id": "R1",
                            "type": "Reactor",
                            "name": "Methanol Reactor",
                            "position": {"x": 200, "y": 300},
                            "parameters": {
                                "temperature": 250,
                                "pressure": 50,
                                "conversion": 0.85,
                                "reactor_type": "CSTR"
                            }
                        },
                        {
                            "id": "T1",
                            "type": "DistillationColumn", 
                            "name": "Methanol Column",
                            "position": {"x": 400, "y": 300},
                            "parameters": {
                                "stages": 20,
                                "reflux_ratio": 2.5,
                                "pressure": 1.0
                            }
                        }
                    ],
                    "connections": [
                        {
                            "from_unit": "R1",
                            "to_unit": "T1",
                            "stream_id": "S1"
                        }
                    ]
                })
            },
            {
                "instruction": "Increase the reactor temperature to 300°C",
                "response": json.dumps({
                    "action": "modify_parameters",
                    "unit_id": "R1",
                    "parameters": {"temperature": 300},
                    "reasoning": "Increasing temperature will improve reaction kinetics and conversion"
                })
            },
            {
                "instruction": "Why is the methanol purity only 85% in the distillation column?",
                "response": json.dumps({
                    "action": "analyze_results",
                    "analysis": {
                        "issue": "Low separation efficiency in distillation column",
                        "causes": [
                            "Insufficient theoretical stages",
                            "Low reflux ratio",
                            "Possible azeotrope formation"
                        ]
                    },
                    "recommendations": [
                        "Increase number of stages to 25-30",
                        "Increase reflux ratio to 3.0",
                        "Consider pressure swing distillation"
                    ]
                })
            },
            {
                "instruction": "Add a heater before the reactor to preheat the feed",
                "response": json.dumps({
                    "action": "add_unit",
                    "unit": {
                        "id": "H1",
                        "type": "Heater",
                        "name": "Feed Heater",
                        "position": {"x": 100, "y": 300},
                        "parameters": {
                            "outlet_temperature": 200,
                            "pressure_drop": 0.1
                        }
                    },
                    "connections": [
                        {
                            "from_unit": "Feed",
                            "to_unit": "H1",
                            "stream_id": "S_feed"
                        },
                        {
                            "from_unit": "H1", 
                            "to_unit": "R1",
                            "stream_id": "S_heated"
                        }
                    ]
                })
            }
        ]
        
        # Add more diverse examples
        for i in range(20):
            sample_data.extend([
                {
                    "instruction": f"Create a process for producing chemical compound {i+1}",
                    "response": json.dumps({
                        "action": "create_flowsheet",
                        "message": f"I've created a basic process for compound {i+1} with reactor and separator",
                        "units": [{"id": f"R{i}", "type": "Reactor", "name": f"Reactor {i}"}]
                    })
                },
                {
                    "instruction": f"Optimize the conversion in reactor R{i}",
                    "response": json.dumps({
                        "action": "analyze_results", 
                        "recommendations": [
                            f"Increase temperature in reactor R{i}",
                            f"Adjust pressure for optimal kinetics",
                            f"Consider catalyst modifications"
                        ]
                    })
                }
            ])
        
        with open(self.dataset_path, 'w') as f:
            for item in sample_data:
                f.write(json.dumps(item) + '\n')
        
        logger.info(f"Created sample dataset with {len(sample_data)} examples")
    
    def train(self):
        """Run the training process"""
        
        logger.info("Starting DeepSeek R1 fine-tuning for DeepSim")
        
        # Initialize Weights & Biases
        if self.config.get('use_wandb', True):
            wandb.init(
                project="deepsim-deepseek-finetune",
                name=f"deepseek-r1-lora-{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                config=self.config
            )
        
        # Setup model and dataset
        model = self.setup_model()
        dataset = self.load_dataset()
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            per_device_train_batch_size=self.config.get('batch_size', 4),
            gradient_accumulation_steps=self.config.get('gradient_accumulation_steps', 4),
            warmup_steps=self.config.get('warmup_steps', 100),
            num_train_epochs=self.config.get('num_epochs', 3),
            learning_rate=self.config.get('learning_rate', 2e-4),
            fp16=False,
            bf16=True,
            logging_steps=10,
            save_steps=500,
            eval_steps=500,
            save_total_limit=3,
            remove_unused_columns=False,
            push_to_hub=False,
            report_to="wandb" if self.config.get('use_wandb', True) else None,
            load_best_model_at_end=True,
            ddp_find_unused_parameters=False,
            group_by_length=True,
            dataloader_pin_memory=False
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            data_collator=data_collator,
        )
        
        # Start training
        logger.info("Starting training...")
        trainer.train()
        
        # Save the final model
        trainer.save_model()
        
        logger.info(f"Training completed. Model saved to {self.output_dir}")
        
        # Upload to Thunder Compute if configured
        if self.thunder_endpoint:
            self.upload_to_thunder()
    
    def upload_to_thunder(self):
        """Upload trained model to Thunder Compute"""
        
        logger.info("Uploading model to Thunder Compute...")
        
        try:
            import requests
            
            # Package model files
            model_files = [
                "adapter_config.json",
                "adapter_model.bin", 
                "training_args.bin"
            ]
            
            # Upload each file
            for file_name in model_files:
                file_path = Path(self.output_dir) / file_name
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        files = {'file': f}
                        headers = {'Authorization': f'Bearer {self.thunder_api_key}'}
                        
                        response = requests.post(
                            f'{self.thunder_endpoint}/upload/model',
                            files=files,
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            logger.info(f"Successfully uploaded {file_name}")
                        else:
                            logger.error(f"Failed to upload {file_name}: {response.text}")
            
            logger.info("Model upload to Thunder Compute completed")
            
        except Exception as e:
            logger.error(f"Failed to upload to Thunder Compute: {e}")

def main():
    parser = argparse.ArgumentParser(description='Fine-tune DeepSeek R1 for DeepSim')
    parser.add_argument('--config', type=str, default='training_config.json',
                       help='Path to training configuration file')
    parser.add_argument('--dataset', type=str, default='dataset.jsonl',
                       help='Path to training dataset')
    parser.add_argument('--output_dir', type=str, default='./deepsim_deepseek_lora',
                       help='Output directory for trained model')
    parser.add_argument('--model_name', type=str, default='deepseek-ai/deepseek-r1-7b',
                       help='Base model name')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {
        'model_name': args.model_name,
        'dataset_path': args.dataset, 
        'output_dir': args.output_dir,
        'batch_size': 4,
        'gradient_accumulation_steps': 4,
        'num_epochs': 3,
        'learning_rate': 2e-4,
        'max_length': 2048,
        'warmup_steps': 100,
        'use_wandb': True
    }
    
    if Path(args.config).exists():
        with open(args.config, 'r') as f:
            file_config = json.load(f)
            config.update(file_config)
    
    # Initialize and run training
    trainer = DeepSeekTrainer(config)
    trainer.train()

if __name__ == "__main__":
    main()