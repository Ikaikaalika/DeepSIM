"""
Database layer with multi-tenant support for DeepSim SaaS
Uses SQLAlchemy with Row Level Security (RLS) for tenant isolation
"""

import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

import asyncpg
from sqlalchemy import create_engine, MetaData, Table, Column, String, DateTime, Boolean, Text, JSON, ForeignKey, Index, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import text
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql://deepsim:password@localhost:5432/deepsim_saas"
ASYNC_DATABASE_URL = "postgresql+asyncpg://deepsim:password@localhost:5432/deepsim_saas"

Base = declarative_base()
metadata = MetaData()

class DatabaseManager:
    """Multi-tenant database manager with automatic tenant isolation"""
    
    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self.current_tenant_id = None
    
    async def initialize(self):
        """Initialize database connections and create tables"""
        try:
            # Create async engine
            self.async_engine = create_async_engine(
                ASYNC_DATABASE_URL,
                echo=True,  # Set to False in production
                pool_size=10,
                max_overflow=20
            )
            
            # Create session factory
            self.AsyncSessionLocal = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            await self.create_tables()
            await self.setup_tenant_isolation()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def create_tables(self):
        """Create database tables with tenant isolation"""
        
        # Define tables
        tenants_table = Table(
            'tenants',
            metadata,
            Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column('name', String(255), nullable=False),
            Column('slug', String(100), unique=True, nullable=False),
            Column('subscription_plan', String(50), nullable=False, default='free'),
            Column('subscription_status', String(20), nullable=False, default='active'),
            Column('settings', JSON, default={}),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            Index('idx_tenants_slug', 'slug'),
            Index('idx_tenants_subscription', 'subscription_plan', 'subscription_status')
        )
        
        users_table = Table(
            'users',
            metadata,
            Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            Column('email', String(255), nullable=False),
            Column('password_hash', String(255), nullable=False),
            Column('first_name', String(100), nullable=False),
            Column('last_name', String(100), nullable=False),
            Column('role', String(50), nullable=False, default='engineer'),
            Column('is_active', Boolean, default=True),
            Column('is_verified', Boolean, default=False),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow),
            Column('last_login', DateTime, nullable=True),
            Index('idx_users_tenant_email', 'tenant_id', 'email', unique=True),
            Index('idx_users_tenant_id', 'tenant_id'),
            Index('idx_users_email', 'email')
        )
        
        flowsheets_table = Table(
            'flowsheets',
            metadata,
            Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            Column('name', String(255), nullable=False),
            Column('description', Text),
            Column('data', JSON, nullable=False),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow),
            Index('idx_flowsheets_tenant_id', 'tenant_id'),
            Index('idx_flowsheets_user_id', 'user_id'),
            Index('idx_flowsheets_name', 'tenant_id', 'name')
        )
        
        simulations_table = Table(
            'simulations',
            metadata,
            Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            Column('flowsheet_id', UUID(as_uuid=True), ForeignKey('flowsheets.id', ondelete='CASCADE'), nullable=False),
            Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            Column('status', String(50), nullable=False, default='pending'),
            Column('results', JSON),
            Column('error_message', Text),
            Column('started_at', DateTime, default=datetime.utcnow),
            Column('completed_at', DateTime, nullable=True),
            Column('execution_time_ms', Integer),
            Index('idx_simulations_tenant_id', 'tenant_id'),
            Index('idx_simulations_flowsheet_id', 'flowsheet_id'),
            Index('idx_simulations_status', 'status')
        )
        
        conversations_table = Table(
            'conversations',
            metadata,
            Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            Column('flowsheet_id', UUID(as_uuid=True), ForeignKey('flowsheets.id', ondelete='SET NULL'), nullable=True),
            Column('context_data', JSON),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow),
            Index('idx_conversations_tenant_id', 'tenant_id'),
            Index('idx_conversations_user_id', 'user_id')
        )
        
        conversation_turns_table = Table(
            'conversation_turns',
            metadata,
            Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            Column('conversation_id', UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
            Column('user_message', Text, nullable=False),
            Column('ai_response', Text, nullable=False),
            Column('task_type', String(100)),
            Column('confidence', Float),
            Column('actions_taken', JSON),
            Column('context', JSON),
            Column('execution_time_ms', Integer),
            Column('model_used', String(100)),
            Column('tokens_used', Integer),
            Column('created_at', DateTime, default=datetime.utcnow),
            Index('idx_turns_tenant_id', 'tenant_id'),
            Index('idx_turns_conversation_id', 'conversation_id'),
            Index('idx_turns_created_at', 'created_at')
        )
        
        feedback_table = Table(
            'feedback',
            metadata,
            Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            Column('tenant_id', UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            Column('turn_id', UUID(as_uuid=True), ForeignKey('conversation_turns.id', ondelete='CASCADE'), nullable=False),
            Column('feedback_type', String(50), nullable=False),
            Column('rating', Integer),
            Column('text_feedback', Text),
            Column('correction', Text),
            Column('tags', JSON),
            Column('outcome', String(50)),
            Column('created_at', DateTime, default=datetime.utcnow),
            Index('idx_feedback_tenant_id', 'tenant_id'),
            Index('idx_feedback_turn_id', 'turn_id'),
            Index('idx_feedback_type_rating', 'feedback_type', 'rating')
        )
        
        # Create all tables
        async with self.async_engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def setup_tenant_isolation(self):
        """Setup Row Level Security (RLS) for tenant isolation"""
        
        tenant_isolated_tables = [
            'users', 'flowsheets', 'simulations', 
            'conversations', 'conversation_turns', 'feedback'
        ]
        
        async with self.async_engine.begin() as conn:
            # Enable RLS on tenant-isolated tables
            for table_name in tenant_isolated_tables:
                await conn.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
                
                # Create RLS policy for tenant isolation
                await conn.execute(text(f"""
                    CREATE POLICY tenant_isolation ON {table_name}
                    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID)
                """))
            
            # Create function to set tenant context
            await conn.execute(text("""
                CREATE OR REPLACE FUNCTION set_tenant_context(tenant_uuid UUID)
                RETURNS void AS $$
                BEGIN
                    PERFORM set_config('app.current_tenant_id', tenant_uuid::text, false);
                END;
                $$ LANGUAGE plpgsql;
            """))
        
        logger.info("Tenant isolation (RLS) setup completed")
    
    @asynccontextmanager
    async def get_session(self, tenant_id: Optional[str] = None):
        """Get database session with optional tenant context"""
        async with self.AsyncSessionLocal() as session:
            try:
                # Set tenant context if provided
                if tenant_id:
                    await session.execute(
                        text("SELECT set_tenant_context(:tenant_id)"),
                        {"tenant_id": tenant_id}
                    )
                
                yield session
                await session.commit()
                
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tenant(self, name: str, slug: str) -> str:
        """Create new tenant and return tenant_id"""
        tenant_id = str(uuid.uuid4())
        
        async with self.get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO tenants (id, name, slug)
                    VALUES (:id, :name, :slug)
                """),
                {"id": tenant_id, "name": name, "slug": slug}
            )
        
        return tenant_id
    
    async def get_tenant_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get tenant by slug"""
        async with self.get_session() as session:
            result = await session.execute(
                text("SELECT * FROM tenants WHERE slug = :slug"),
                {"slug": slug}
            )
            row = result.first()
            if row:
                return dict(row._mapping)
            return None
    
    async def create_user(self, tenant_id: str, user_data: Dict[str, Any]) -> str:
        """Create new user in tenant context"""
        user_id = str(uuid.uuid4())
        
        async with self.get_session(tenant_id) as session:
            await session.execute(
                text("""
                    INSERT INTO users (id, tenant_id, email, password_hash, 
                                     first_name, last_name, role)
                    VALUES (:id, :tenant_id, :email, :password_hash, 
                           :first_name, :last_name, :role)
                """),
                {
                    "id": user_id,
                    "tenant_id": tenant_id,
                    **user_data
                }
            )
        
        return user_id
    
    async def get_user_by_email(self, tenant_id: str, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email within tenant context"""
        async with self.get_session(tenant_id) as session:
            result = await session.execute(
                text("SELECT * FROM users WHERE email = :email"),
                {"email": email}
            )
            row = result.first()
            if row:
                return dict(row._mapping)
            return None
    
    async def create_flowsheet(self, tenant_id: str, user_id: str, 
                             name: str, description: str, data: Dict[str, Any]) -> str:
        """Create flowsheet in tenant context"""
        flowsheet_id = str(uuid.uuid4())
        
        async with self.get_session(tenant_id) as session:
            await session.execute(
                text("""
                    INSERT INTO flowsheets (id, tenant_id, user_id, name, description, data)
                    VALUES (:id, :tenant_id, :user_id, :name, :description, :data)
                """),
                {
                    "id": flowsheet_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "name": name,
                    "description": description,
                    "data": data
                }
            )
        
        return flowsheet_id
    
    async def get_tenant_flowsheets(self, tenant_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all flowsheets for tenant (optionally filtered by user)"""
        async with self.get_session(tenant_id) as session:
            query = "SELECT * FROM flowsheets"
            params = {}
            
            if user_id:
                query += " WHERE user_id = :user_id"
                params["user_id"] = user_id
            
            query += " ORDER BY updated_at DESC"
            
            result = await session.execute(text(query), params)
            return [dict(row._mapping) for row in result]
    
    async def log_conversation_turn(self, tenant_id: str, turn_data: Dict[str, Any]) -> str:
        """Log conversation turn for feedback/training"""
        turn_id = str(uuid.uuid4())
        
        async with self.get_session(tenant_id) as session:
            await session.execute(
                text("""
                    INSERT INTO conversation_turns (
                        id, tenant_id, conversation_id, user_message, ai_response,
                        task_type, confidence, actions_taken, context, 
                        execution_time_ms, model_used, tokens_used
                    ) VALUES (
                        :id, :tenant_id, :conversation_id, :user_message, :ai_response,
                        :task_type, :confidence, :actions_taken, :context,
                        :execution_time_ms, :model_used, :tokens_used
                    )
                """),
                {
                    "id": turn_id,
                    "tenant_id": tenant_id,
                    **turn_data
                }
            )
        
        return turn_id
    
    async def close(self):
        """Close database connections"""
        if self.async_engine:
            await self.async_engine.dispose()
        logger.info("Database connections closed")

# Global database manager
db_manager = DatabaseManager()

# Dependency for FastAPI
async def get_db_session():
    """FastAPI dependency for database session"""
    async with db_manager.get_session() as session:
        yield session

async def get_tenant_db_session(tenant_id: str):
    """FastAPI dependency for tenant-isolated database session"""
    async with db_manager.get_session(tenant_id) as session:
        yield session