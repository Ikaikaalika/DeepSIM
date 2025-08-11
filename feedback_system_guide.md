# DeepSim Feedback System Guide

The DeepSim feedback system automatically captures all AI interactions and user feedback to continuously improve the AI model through fine-tuning and retraining.

## 🎯 Key Features

### 1. Automatic Interaction Logging
- **Every AI conversation** is automatically logged with full context
- **Performance metrics** including confidence, execution time, and success rates
- **User context** including current flowsheet state and task type
- **Model metadata** tracking which AI model was used

### 2. Rich Feedback Collection
- **Quick feedback**: 👍/👎 buttons on every AI response
- **Detailed feedback**: Text feedback and corrections
- **Categorical tags**: Accuracy, Helpfulness, Completeness, Clarity, Engineering Quality
- **Outcome tracking**: Success/Failure/Partial Success classification

### 3. Training Data Export
- **Multiple formats**: OpenAI, Anthropic, and custom DeepSim formats
- **Quality filtering**: Export only high-quality interactions
- **Automatic formatting**: Ready-to-use training data for fine-tuning

## 📊 Database Schema

The system uses SQLite with the following tables:

```sql
-- Conversations: High-level conversation tracking
conversations (conversation_id, session_id, user_id, start_time, end_time, total_turns, final_outcome, flowsheet_id)

-- Conversation Turns: Individual message exchanges
conversation_turns (turn_id, conversation_id, user_message, ai_response, task_type, confidence, actions_taken, execution_time, model_used, tokens_used)

-- User Feedback: Ratings and detailed feedback
user_feedback (feedback_id, turn_id, feedback_type, rating, text_feedback, correction, tags, outcome)

-- Performance Metrics: Technical performance data
performance_metrics (metric_id, turn_id, processing_time, model_latency, action_success_rate, convergence_achieved, parameter_quality)

-- Training Exports: Track exported training data
training_exports (export_id, export_timestamp, total_conversations, total_turns, file_path, format)
```

## 🚀 Usage Examples

### Backend API Usage

```python
# All AI interactions are automatically logged
response = await ai_engine.process_request(ai_request)

# Feedback is submitted via API
POST /feedback
{
    "turn_id": "abc123",
    "conversation_id": "conv456", 
    "feedback_type": "thumbs_up",
    "rating": 5,
    "text_feedback": "Great explanation of distillation!",
    "tags": ["accuracy", "helpfulness"]
}
```

### Frontend Integration

```javascript
// Every AI message includes feedback buttons
const messageId = addMessageToChat('assistant', response.message, {
    turn_id: response.turn_id,
    conversation_id: response.conversation_id,
    confidence: response.confidence
});

// Users can provide feedback
submitFeedback(messageId, 'thumbs_up', 5);
submitDetailedFeedback(messageId, {
    text_feedback: "Could be more specific about temperature ranges",
    correction: "The optimal temperature for this reaction is 350-400K",
    tags: ["completeness", "engineering"]
});
```

## 📈 Analytics Dashboard

Get real-time analytics on AI performance:

```bash
GET /analytics/feedback
{
    "basic_stats": {
        "total_conversations": 150,
        "total_turns": 450,
        "avg_confidence": 0.85,
        "avg_execution_time": 1200
    },
    "feedback_stats": {
        "avg_rating": 4.2,
        "positive_feedback": 120,
        "negative_feedback": 15
    },
    "task_breakdown": [
        {"task_type": "design_flowsheet", "count": 200, "avg_confidence": 0.87},
        {"task_type": "optimize_process", "count": 150, "avg_confidence": 0.82}
    ],
    "problem_areas": [
        {
            "task_type": "analyze_simulation",
            "rating": 2,
            "text_feedback": "Analysis was too generic, needed more specific recommendations"
        }
    ]
}
```

## 🔄 Training Data Export

### Using the Training Manager CLI

```bash
# Export last 30 days of high-quality interactions
python training_manager.py --export --days 30 --min-rating 4 --format openai

# Include negative feedback for correction learning
python training_manager.py --export --days 7 --min-rating 2 --format openai

# Start continuous monitoring
python training_manager.py --monitor

# Analyze conversation patterns
python training_manager.py --analyze

# Clean up old data
python training_manager.py --cleanup 90
```

### Training Data Formats

#### OpenAI Format
```jsonl
{"messages": [
    {"role": "system", "content": "You are an expert chemical process engineer..."},
    {"role": "user", "content": "Design a benzene-toluene separation process"},
    {"role": "assistant", "content": "I'll design a rigorous distillation column..."}
]}
```

#### Anthropic Format  
```jsonl
{
    "input": {
        "system": "You are an expert chemical process engineer...",
        "user": "Design a benzene-toluene separation process"
    },
    "output": "I'll design a rigorous distillation column...",
    "metadata": {
        "task_type": "design_flowsheet",
        "confidence": 0.92,
        "rating": 5
    }
}
```

#### DeepSim Format (Full Context)
```jsonl
{
    "conversation_id": "conv_123",
    "task_type": "design_flowsheet", 
    "user_message": "Design a benzene-toluene separation process",
    "ai_response": "I'll design a rigorous distillation column...",
    "actions_taken": [
        {"type": "create_unit", "unit_type": "DistillationColumn", "parameters": {...}}
    ],
    "context": {"current_units": 0, "unit_types": []},
    "confidence": 0.92,
    "rating": 5,
    "feedback": "Excellent design with realistic parameters",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🔧 Fine-tuning Workflow

### 1. Data Collection
- Users interact with AI through the interface
- All conversations automatically logged to database
- Feedback collected through UI elements

### 2. Quality Assessment
- Filter interactions by rating (≥4 for positive examples)
- Include corrected responses from negative feedback
- Tag-based filtering for specific improvement areas

### 3. Training Data Preparation
- Export in appropriate format for target platform
- Include system prompts specialized for process engineering
- Balance dataset across different task types

### 4. Model Fine-tuning
- Upload to Thunder Compute, OpenAI, or Anthropic
- Monitor training progress and validation metrics
- Deploy improved model and measure performance

### 5. Continuous Improvement
- Monitor feedback trends and identify declining performance
- Automatically trigger retraining when quality drops
- A/B test new models against current production

## 📊 Monitoring and Alerts

### Automatic Quality Monitoring
```python
# Triggers when performance declines
if avg_rating < 3.5 or negative_feedback > 10:
    print("📉 Performance declining - triggering retraining")
    await generate_training_export(
        days_back=7,
        min_rating=2,  # Include corrections
        format_type="openai",
        auto_upload=True
    )
```

### Problem Area Detection
- Identify specific task types with low ratings
- Extract common themes from negative feedback
- Generate targeted training data for problem areas

## 🔐 Privacy and Data Management

### Data Retention
- Training data retention: 90 days default
- Automatic cleanup of old conversations
- User consent tracking for training data usage

### Anonymization  
- Remove user identifiers from training data
- Hash conversation IDs for privacy
- Aggregate analytics without personal information

## 🎯 Success Metrics

Track these KPIs to measure AI improvement:

1. **Response Quality**: Average user rating (target: ≥4.0/5)
2. **Task Success Rate**: Percentage of successful outcomes (target: ≥85%)
3. **User Satisfaction**: Positive feedback ratio (target: ≥80%)
4. **Model Confidence**: AI confidence correlation with user ratings
5. **Engineering Accuracy**: Technical correctness of process designs
6. **Response Time**: Average processing time (target: <2 seconds)

## 🔄 Integration with Thunder Compute

The system is designed to work seamlessly with Thunder Compute for DeepSeek R1 fine-tuning:

1. **Automatic Export**: Training data in DeepSeek-compatible format
2. **Thunder CLI Integration**: Direct upload to Thunder platform
3. **LoRA/QLoRA Support**: Efficient fine-tuning with limited resources
4. **Model Versioning**: Track performance across model iterations

This comprehensive feedback system ensures that DeepSim's AI continuously learns from user interactions and becomes more accurate, helpful, and specialized for chemical process engineering tasks.