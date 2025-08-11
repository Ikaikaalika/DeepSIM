"""
Feedback and Logging System for LLM Training
Captures all AI interactions, user feedback, and performance metrics
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import asyncio
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    DETAILED = "detailed"
    CORRECTION = "correction"
    IMPROVEMENT = "improvement"

class InteractionOutcome(Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    USER_ABANDONED = "user_abandoned"
    ERROR = "error"

@dataclass
class ConversationTurn:
    """Single conversation turn (user message + AI response)"""
    turn_id: str
    conversation_id: str
    timestamp: str
    user_message: str
    ai_response: str
    task_type: str
    confidence: float
    actions_taken: List[Dict[str, Any]]
    context: Dict[str, Any]
    execution_time: float  # milliseconds
    model_used: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None

@dataclass
class UserFeedback:
    """User feedback on AI interaction"""
    feedback_id: str
    turn_id: str
    conversation_id: str
    timestamp: str
    feedback_type: FeedbackType
    rating: Optional[int] = None  # 1-5 scale
    text_feedback: Optional[str] = None
    correction: Optional[str] = None  # What the AI should have said/done
    tags: List[str] = None  # Categories like "accuracy", "helpfulness", etc.
    outcome: Optional[InteractionOutcome] = None

@dataclass
class ProcessingMetrics:
    """Performance metrics for the interaction"""
    processing_time: float
    model_latency: float
    action_success_rate: float
    convergence_achieved: bool
    parameter_quality: float  # 0-1 score based on engineering validity

class FeedbackDatabase:
    """SQLite database for storing feedback and conversation data"""
    
    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    user_id TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    total_turns INTEGER,
                    final_outcome TEXT,
                    flowsheet_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    turn_id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    turn_number INTEGER,
                    timestamp TIMESTAMP,
                    user_message TEXT,
                    ai_response TEXT,
                    task_type TEXT,
                    confidence REAL,
                    actions_taken TEXT,  -- JSON
                    context TEXT,        -- JSON
                    execution_time REAL,
                    model_used TEXT,
                    tokens_used INTEGER,
                    cost_estimate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
                );
                
                CREATE TABLE IF NOT EXISTS user_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    turn_id TEXT,
                    conversation_id TEXT,
                    timestamp TIMESTAMP,
                    feedback_type TEXT,
                    rating INTEGER,
                    text_feedback TEXT,
                    correction TEXT,
                    tags TEXT,  -- JSON array
                    outcome TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (turn_id) REFERENCES conversation_turns(turn_id),
                    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
                );
                
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    turn_id TEXT,
                    processing_time REAL,
                    model_latency REAL,
                    action_success_rate REAL,
                    convergence_achieved BOOLEAN,
                    parameter_quality REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (turn_id) REFERENCES conversation_turns(turn_id)
                );
                
                CREATE TABLE IF NOT EXISTS training_exports (
                    export_id TEXT PRIMARY KEY,
                    export_timestamp TIMESTAMP,
                    date_range_start TIMESTAMP,
                    date_range_end TIMESTAMP,
                    total_conversations INTEGER,
                    total_turns INTEGER,
                    feedback_included BOOLEAN,
                    file_path TEXT,
                    format TEXT,  -- 'openai', 'anthropic', 'jsonl', etc.
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_turns_conversation ON conversation_turns(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_turn ON user_feedback(turn_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_rating ON user_feedback(rating);
                CREATE INDEX IF NOT EXISTS idx_turns_timestamp ON conversation_turns(timestamp);
            """)
    
    def save_conversation_turn(self, turn: ConversationTurn):
        """Save a conversation turn to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO conversation_turns 
                (turn_id, conversation_id, timestamp, user_message, ai_response, 
                 task_type, confidence, actions_taken, context, execution_time,
                 model_used, tokens_used, cost_estimate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                turn.turn_id, turn.conversation_id, turn.timestamp,
                turn.user_message, turn.ai_response, turn.task_type,
                turn.confidence, json.dumps(turn.actions_taken),
                json.dumps(turn.context), turn.execution_time,
                turn.model_used, turn.tokens_used, turn.cost_estimate
            ))
    
    def save_feedback(self, feedback: UserFeedback):
        """Save user feedback to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO user_feedback 
                (feedback_id, turn_id, conversation_id, timestamp, feedback_type,
                 rating, text_feedback, correction, tags, outcome)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                feedback.feedback_id, feedback.turn_id, feedback.conversation_id,
                feedback.timestamp, feedback.feedback_type.value,
                feedback.rating, feedback.text_feedback, feedback.correction,
                json.dumps(feedback.tags) if feedback.tags else None,
                feedback.outcome.value if feedback.outcome else None
            ))
    
    def get_training_data(self, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         min_rating: Optional[int] = None,
                         include_negative: bool = True) -> List[Dict[str, Any]]:
        """Export training data for fine-tuning"""
        
        query = """
            SELECT ct.*, uf.rating, uf.text_feedback, uf.correction, uf.outcome
            FROM conversation_turns ct
            LEFT JOIN user_feedback uf ON ct.turn_id = uf.turn_id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND ct.timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND ct.timestamp <= ?"
            params.append(end_date)
        
        if min_rating:
            query += " AND (uf.rating IS NULL OR uf.rating >= ?)"
            params.append(min_rating)
        
        if not include_negative:
            query += " AND (uf.rating IS NULL OR uf.rating >= 3)"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

class FeedbackCollector:
    """Main feedback collection and management system"""
    
    def __init__(self, db_path: str = "feedback.db"):
        self.db = FeedbackDatabase(db_path)
        self.active_conversations: Dict[str, Dict] = {}
        
    async def log_conversation_turn(self,
                                  conversation_id: str,
                                  user_message: str,
                                  ai_response: str,
                                  task_type: str,
                                  confidence: float,
                                  actions_taken: List[Dict[str, Any]],
                                  context: Dict[str, Any],
                                  execution_time: float,
                                  model_used: str,
                                  tokens_used: Optional[int] = None) -> str:
        """Log a conversation turn and return turn_id"""
        
        turn_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        turn = ConversationTurn(
            turn_id=turn_id,
            conversation_id=conversation_id,
            timestamp=timestamp,
            user_message=user_message,
            ai_response=ai_response,
            task_type=task_type,
            confidence=confidence,
            actions_taken=actions_taken,
            context=context,
            execution_time=execution_time,
            model_used=model_used,
            tokens_used=tokens_used
        )
        
        self.db.save_conversation_turn(turn)
        logger.info(f"Logged conversation turn {turn_id} for conversation {conversation_id}")
        
        return turn_id
    
    async def collect_feedback(self,
                              turn_id: str,
                              conversation_id: str,
                              feedback_type: FeedbackType,
                              rating: Optional[int] = None,
                              text_feedback: Optional[str] = None,
                              correction: Optional[str] = None,
                              tags: Optional[List[str]] = None,
                              outcome: Optional[InteractionOutcome] = None):
        """Collect user feedback on an interaction"""
        
        feedback_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        feedback = UserFeedback(
            feedback_id=feedback_id,
            turn_id=turn_id,
            conversation_id=conversation_id,
            timestamp=timestamp,
            feedback_type=feedback_type,
            rating=rating,
            text_feedback=text_feedback,
            correction=correction,
            tags=tags,
            outcome=outcome
        )
        
        self.db.save_feedback(feedback)
        logger.info(f"Collected feedback {feedback_id} for turn {turn_id}")
        
        # Log feedback for immediate analysis
        if rating is not None and rating <= 2:
            logger.warning(f"Low rating ({rating}/5) for turn {turn_id}: {text_feedback}")
        elif rating is not None and rating >= 4:
            logger.info(f"High rating ({rating}/5) for turn {turn_id}")
    
    async def export_training_data(self,
                                  format_type: str = "openai",
                                  start_date: Optional[str] = None,
                                  end_date: Optional[str] = None,
                                  min_rating: int = 3,
                                  output_path: Optional[str] = None) -> str:
        """Export training data in various formats for fine-tuning"""
        
        training_data = self.db.get_training_data(
            start_date=start_date,
            end_date=end_date,
            min_rating=min_rating
        )
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"training_data_{format_type}_{timestamp}.jsonl"
        
        export_count = 0
        
        with open(output_path, 'w') as f:
            for item in training_data:
                # Skip items with negative feedback unless they have corrections
                if item.get('rating') and item['rating'] < 3 and not item.get('correction'):
                    continue
                
                if format_type == "openai":
                    # Format for OpenAI fine-tuning
                    messages = [
                        {"role": "system", "content": self._get_system_prompt(item['task_type'])},
                        {"role": "user", "content": item['user_message']}
                    ]
                    
                    # Use correction if available, otherwise use original AI response
                    assistant_content = item.get('correction') or item['ai_response']
                    messages.append({"role": "assistant", "content": assistant_content})
                    
                    training_example = {"messages": messages}
                    
                elif format_type == "anthropic":
                    # Format for Anthropic fine-tuning
                    training_example = {
                        "input": {
                            "system": self._get_system_prompt(item['task_type']),
                            "user": item['user_message']
                        },
                        "output": item.get('correction') or item['ai_response'],
                        "metadata": {
                            "task_type": item['task_type'],
                            "confidence": item['confidence'],
                            "rating": item.get('rating')
                        }
                    }
                
                elif format_type == "deepsim":
                    # Custom DeepSim format with full context
                    training_example = {
                        "conversation_id": item['conversation_id'],
                        "task_type": item['task_type'],
                        "user_message": item['user_message'],
                        "ai_response": item.get('correction') or item['ai_response'],
                        "actions_taken": json.loads(item['actions_taken'] or '[]'),
                        "context": json.loads(item['context'] or '{}'),
                        "confidence": item['confidence'],
                        "rating": item.get('rating'),
                        "feedback": item.get('text_feedback'),
                        "timestamp": item['timestamp']
                    }
                
                f.write(json.dumps(training_example) + '\n')
                export_count += 1
        
        # Log the export
        export_id = str(uuid.uuid4())
        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute("""
                INSERT INTO training_exports 
                (export_id, export_timestamp, date_range_start, date_range_end,
                 total_conversations, total_turns, feedback_included, file_path, format)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                export_id, datetime.now(timezone.utc).isoformat(),
                start_date, end_date, 0, export_count, True, output_path, format_type
            ))
        
        logger.info(f"Exported {export_count} training examples to {output_path}")
        return output_path
    
    def _get_system_prompt(self, task_type: str) -> str:
        """Get appropriate system prompt based on task type"""
        
        base_prompt = """You are an expert AI chemical process engineer specializing in industrial process design and optimization. You have deep knowledge of unit operations, thermodynamics, process simulation, and industrial best practices."""
        
        task_prompts = {
            "design_flowsheet": base_prompt + " Focus on creating complete, realistic process flowsheets with proper unit operations and realistic parameters.",
            "optimize_process": base_prompt + " Focus on improving existing processes through parameter optimization, energy integration, and efficiency improvements.",
            "analyze_simulation": base_prompt + " Focus on analyzing simulation results and providing actionable recommendations for process improvements.",
            "autonomous_test": base_prompt + " Focus on designing comprehensive testing protocols and validation procedures for process designs."
        }
        
        return task_prompts.get(task_type, base_prompt)
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get analytics and metrics on feedback and performance"""
        
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Basic statistics
            stats = conn.execute("""
                SELECT 
                    COUNT(DISTINCT conversation_id) as total_conversations,
                    COUNT(*) as total_turns,
                    AVG(confidence) as avg_confidence,
                    AVG(execution_time) as avg_execution_time
                FROM conversation_turns
                WHERE timestamp >= datetime('now', '-30 days')
            """).fetchone()
            
            # Feedback statistics
            feedback_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_feedback
                FROM user_feedback
                WHERE timestamp >= datetime('now', '-30 days')
            """).fetchone()
            
            # Task type breakdown
            task_breakdown = conn.execute("""
                SELECT task_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM conversation_turns
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY task_type
            """).fetchall()
            
            # Recent low-rated interactions for improvement
            problem_areas = conn.execute("""
                SELECT ct.task_type, ct.user_message, ct.ai_response, uf.rating, uf.text_feedback
                FROM conversation_turns ct
                JOIN user_feedback uf ON ct.turn_id = uf.turn_id
                WHERE uf.rating <= 2 AND uf.timestamp >= datetime('now', '-7 days')
                ORDER BY uf.timestamp DESC
                LIMIT 10
            """).fetchall()
            
            return {
                "basic_stats": dict(stats),
                "feedback_stats": dict(feedback_stats),
                "task_breakdown": [dict(row) for row in task_breakdown],
                "problem_areas": [dict(row) for row in problem_areas],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

# Global feedback collector instance
feedback_collector = FeedbackCollector()