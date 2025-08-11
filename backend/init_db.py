#!/usr/bin/env python3
"""
Database initialization script for DeepSim SaaS
Creates PostgreSQL database and initial tables
"""

import asyncio
import logging
from database import db_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Initialize database and create tables"""
    try:
        logger.info("🚀 Starting database initialization for DeepSim SaaS...")
        
        # Initialize database manager
        await db_manager.initialize()
        
        logger.info("✅ Database initialization completed successfully!")
        logger.info("🔐 Multi-tenant isolation (RLS) is active")
        logger.info("📊 All tables created with proper indexes")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    finally:
        # Close database connections
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())