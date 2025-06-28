# DeepSIM - DeepSeek R1 Fine-tuning System with DWSIM Integration

A comprehensive system that fine-tunes DeepSeek R1 for text-to-diagram and text-to-simulation tasks using DWSIM, with reinforcement learning from simulation results and RLHF capabilities.

## Overview

DeepSIM creates a seamless workflow from natural language process descriptions to validated DWSIM simulations, with continuous improvement through reinforcement learning and user feedback. The system combines advanced language model fine-tuning with chemical process simulation to enable engineers to describe processes in plain English and automatically generate complete simulation models.

## Key Features

- **DeepSeek R1 Fine-tuning**: Custom fine-tuning pipeline with QLoRA optimization
- **DWSIM Integration**: Direct Python API integration for simulation automation  
- **Reinforcement Learning**: PPO-based training with simulation feedback rewards
- **GUI Application**: Cross-platform interface with real-time model interaction
- **Thunder Compute**: Distributed training for scalable model development
- **Feedback System**: Human-in-the-loop learning from user corrections

## System Architecture

### Core Components
- **Main Application**: Python-based modular architecture
- **GUI Framework**: Tkinter/PyQt6 for cross-platform compatibility
- **ML Framework**: transformers, torch, and trl for model fine-tuning
- **Compute Backend**: Thunder Compute for distributed training
- **Database**: SQLite for training data and simulation results
- **API Layer**: FastAPI for model serving and DWSIM communication

### Supported Process Types
- Distillation columns
- Heat exchangers  
- Reactors (CSTR, PFR, batch)
- Separators and flash tanks
- Pumps and compressors
- Mixers and splitters
- Cooling towers
- Absorption/stripping columns

## Project Structure

```
DeepSIM/
├── src/
│   ├── models/              # DeepSeek R1 fine-tuning modules
│   ├── dwsim_integration/   # DWSIM Python API interface
│   ├── gui/                 # User interface components
│   ├── data/                # Database and preprocessing
│   └── api/                 # FastAPI server endpoints
├── config/                  # Configuration files
├── data/                    # Training and simulation data
├── models/                  # Model checkpoints
└── requirements.txt
```

## Installation

1. Install Python 3.9+ and CUDA toolkit
2. Set up virtual environment
3. Install DWSIM and configure pythonnet
4. Configure Thunder Compute access
5. Install dependencies: `pip install -r requirements.txt`

## Usage

The system provides multiple interaction modes:
- GUI application for interactive process design
- API endpoints for programmatic access
- Training dashboard for model fine-tuning
- Feedback system for continuous improvement

## Fine-tuning Configuration

- **Base Model**: DeepSeek R1 (latest version)
- **Method**: QLoRA with 4-bit quantization
- **Training**: PPO with simulation-based rewards
- **Architecture**: Multi-GPU distributed training
- **Optimization**: Gradient accumulation and memory management
