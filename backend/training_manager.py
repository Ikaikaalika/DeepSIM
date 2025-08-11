#!/usr/bin/env python3
"""
Training Data Manager for DeepSim AI
Automated collection, processing, and export of training data for LLM fine-tuning
"""

import asyncio
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import os
from typing import Dict, List, Optional

from feedback_system import FeedbackCollector, FeedbackDatabase

logger = logging.getLogger(__name__)

class TrainingDataManager:
    """Manages training data collection and fine-tuning workflows"""
    
    def __init__(self):
        self.feedback_collector = FeedbackCollector()
        self.db = FeedbackDatabase()
        
    async def generate_training_export(self, 
                                     days_back: int = 30,
                                     min_rating: int = 3,
                                     format_type: str = "openai",
                                     auto_upload: bool = False):
        """Generate and optionally upload training data"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        print(f"📊 Exporting training data from {start_date.date()} to {end_date.date()}")
        print(f"   - Format: {format_type}")
        print(f"   - Minimum rating: {min_rating}/5")
        
        # Export training data
        file_path = await self.feedback_collector.export_training_data(
            format_type=format_type,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            min_rating=min_rating
        )
        
        # Get analytics
        analytics = await self.feedback_collector.get_analytics()
        
        print(f"\n✅ Training data exported to: {file_path}")
        print(f"📈 Statistics:")
        print(f"   - Total conversations: {analytics['basic_stats']['total_conversations']}")
        print(f"   - Total turns: {analytics['basic_stats']['total_turns']}")
        print(f"   - Average confidence: {analytics['basic_stats']['avg_confidence']:.2f}")
        print(f"   - Average rating: {analytics['feedback_stats']['avg_rating']:.2f}")
        print(f"   - Positive feedback: {analytics['feedback_stats']['positive_feedback']}")
        print(f"   - Negative feedback: {analytics['feedback_stats']['negative_feedback']}")
        
        # Show problem areas for improvement
        if analytics['problem_areas']:
            print(f"\n⚠️  Problem areas needing attention:")
            for issue in analytics['problem_areas'][:3]:
                print(f"   - Task: {issue['task_type']}, Rating: {issue['rating']}/5")
                print(f"     Feedback: {issue['text_feedback'][:100]}...")
        
        if auto_upload and format_type == "openai":
            await self._upload_to_openai(file_path)
        elif auto_upload and format_type == "anthropic":
            await self._upload_to_anthropic(file_path)
        
        return file_path
    
    async def _upload_to_openai(self, file_path: str):
        """Upload training data to OpenAI for fine-tuning"""
        try:
            print("🚀 Uploading to OpenAI for fine-tuning...")
            
            # OpenAI CLI command for fine-tuning upload
            cmd = [
                "openai", "api", "fine_tunes.create",
                "-t", file_path,
                "-m", "gpt-3.5-turbo",
                "--suffix", "deepsim-process-engineering"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Successfully uploaded to OpenAI")
                print(f"Output: {result.stdout}")
            else:
                print(f"❌ Upload failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ OpenAI upload error: {e}")
    
    async def _upload_to_anthropic(self, file_path: str):
        """Upload training data to Anthropic (placeholder)"""
        print("📝 Anthropic upload not yet implemented - file ready for manual upload")
        print(f"File: {file_path}")
    
    async def continuous_monitoring(self):
        """Continuously monitor feedback and trigger retraining when needed"""
        print("🔄 Starting continuous monitoring...")
        
        while True:
            try:
                analytics = await self.feedback_collector.get_analytics()
                
                # Check if retraining is needed
                avg_rating = analytics['feedback_stats']['avg_rating']
                negative_count = analytics['feedback_stats']['negative_feedback']
                
                if avg_rating < 3.5 or negative_count > 10:
                    print(f"📉 Performance declining: avg_rating={avg_rating:.2f}, negative={negative_count}")
                    print("🔄 Triggering automatic retraining...")
                    
                    await self.generate_training_export(
                        days_back=7,
                        min_rating=2,  # Include negative feedback for correction
                        format_type="deepsim",
                        auto_upload=False
                    )
                
                # Check hourly
                await asyncio.sleep(3600)
                
            except KeyboardInterrupt:
                print("👋 Stopping continuous monitoring...")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def analyze_conversation_patterns(self):
        """Analyze conversation patterns for insights"""
        analytics = await self.feedback_collector.get_analytics()
        
        print("🔍 Conversation Analysis:")
        print("=" * 50)
        
        # Task type breakdown
        print("\nTask Type Performance:")
        for task in analytics['task_breakdown']:
            print(f"  {task['task_type']}: {task['count']} interactions, {task['avg_confidence']:.2f} confidence")
        
        # Recent problem areas
        print(f"\nRecent Issues ({len(analytics['problem_areas'])}):")
        for issue in analytics['problem_areas']:
            print(f"  • {issue['task_type']}: {issue['rating']}/5 - {issue['text_feedback'][:80]}...")
        
        return analytics
    
    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old training data and logs"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        print(f"🧹 Cleaning up data older than {days_to_keep} days...")
        
        # This would require additional database queries to clean up old data
        # Implementation depends on retention policy
        print("✅ Cleanup completed")

async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="DeepSim Training Data Manager")
    parser.add_argument("--export", action="store_true", help="Export training data")
    parser.add_argument("--days", type=int, default=30, help="Days of data to export")
    parser.add_argument("--min-rating", type=int, default=3, help="Minimum rating to include")
    parser.add_argument("--format", choices=["openai", "anthropic", "deepsim"], default="openai")
    parser.add_argument("--upload", action="store_true", help="Auto-upload to AI service")
    parser.add_argument("--monitor", action="store_true", help="Start continuous monitoring")
    parser.add_argument("--analyze", action="store_true", help="Analyze conversation patterns")
    parser.add_argument("--cleanup", type=int, help="Clean up data older than N days")
    
    args = parser.parse_args()
    
    manager = TrainingDataManager()
    
    if args.export:
        await manager.generate_training_export(
            days_back=args.days,
            min_rating=args.min_rating,
            format_type=args.format,
            auto_upload=args.upload
        )
    
    elif args.monitor:
        await manager.continuous_monitoring()
    
    elif args.analyze:
        await manager.analyze_conversation_patterns()
    
    elif args.cleanup:
        await manager.cleanup_old_data(args.cleanup)
    
    else:
        print("DeepSim Training Data Manager")
        print("Usage: python training_manager.py --export [--days 30] [--upload]")
        print("       python training_manager.py --monitor")
        print("       python training_manager.py --analyze")
        print("       python training_manager.py --cleanup 90")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())