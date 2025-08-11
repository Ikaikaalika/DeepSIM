"""
Authentication and Authorization System for DeepSim SaaS
Implements JWT-based authentication with multi-tenant support
"""

import jwt
import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = "your-super-secret-jwt-key-change-in-production"  # TODO: Move to env vars
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 30

class Permission(Enum):
    VIEW_FLOWSHEETS = "view_flowsheets"
    CREATE_FLOWSHEETS = "create_flowsheets"
    EDIT_FLOWSHEETS = "edit_flowsheets"
    DELETE_FLOWSHEETS = "delete_flowsheets"
    RUN_SIMULATIONS = "run_simulations"
    MANAGE_TEAM = "manage_team"
    VIEW_ANALYTICS = "view_analytics"
    ADMIN_TENANT = "admin_tenant"
    SUPER_ADMIN = "super_admin"

class Role(Enum):
    VIEWER = "viewer"
    ENGINEER = "engineer" 
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.VIEWER: [
        Permission.VIEW_FLOWSHEETS
    ],
    Role.ENGINEER: [
        Permission.VIEW_FLOWSHEETS,
        Permission.CREATE_FLOWSHEETS,
        Permission.EDIT_FLOWSHEETS,
        Permission.RUN_SIMULATIONS
    ],
    Role.ADMIN: [
        Permission.VIEW_FLOWSHEETS,
        Permission.CREATE_FLOWSHEETS,
        Permission.EDIT_FLOWSHEETS,
        Permission.DELETE_FLOWSHEETS,
        Permission.RUN_SIMULATIONS,
        Permission.MANAGE_TEAM,
        Permission.VIEW_ANALYTICS,
        Permission.ADMIN_TENANT
    ],
    Role.SUPER_ADMIN: [perm for perm in Permission]  # All permissions
}

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    role: Role = Role.ENGINEER
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

class Tenant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str
    subscription_plan: str = "free"
    subscription_status: str = "active"
    settings: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserRegistration(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    company_name: str = Field(..., min_length=1, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter') 
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    email: str
    password: str

class AuthToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    tenant_id: str
    role: str

class TokenPayload(BaseModel):
    user_id: str
    tenant_id: str
    role: str
    permissions: List[str]
    subscription_plan: str
    exp: datetime
    iat: datetime
    type: str = "access"

class AuthService:
    def __init__(self):
        # In production, use proper database
        self.users: Dict[str, User] = {}
        self.tenants: Dict[str, Tenant] = {}
        self.users_by_email: Dict[str, str] = {}  # email -> user_id mapping
        self.tenant_users: Dict[str, List[str]] = {}  # tenant_id -> [user_ids]
        
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_slug(self, company_name: str) -> str:
        """Generate URL-safe slug from company name"""
        slug = company_name.lower().replace(' ', '-').replace('&', 'and')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        # Ensure uniqueness
        counter = 1
        original_slug = slug
        while any(t.slug == slug for t in self.tenants.values()):
            slug = f"{original_slug}-{counter}"
            counter += 1
            
        return slug
    
    async def register_user(self, registration: UserRegistration) -> AuthToken:
        """Register new user and create tenant"""
        
        # Check if email already exists
        if registration.email in self.users_by_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create tenant
        tenant = Tenant(
            name=registration.company_name,
            slug=self.generate_slug(registration.company_name)
        )
        
        # Create user
        user = User(
            tenant_id=tenant.id,
            email=registration.email,
            password_hash=self.hash_password(registration.password),
            first_name=registration.first_name,
            last_name=registration.last_name,
            role=Role.ADMIN  # First user is admin
        )
        
        # Store in memory (use database in production)
        self.tenants[tenant.id] = tenant
        self.users[user.id] = user
        self.users_by_email[user.email] = user.id
        
        if tenant.id not in self.tenant_users:
            self.tenant_users[tenant.id] = []
        self.tenant_users[tenant.id].append(user.id)
        
        # Generate tokens
        return self.generate_tokens(user, tenant)
    
    async def login_user(self, login: UserLogin) -> AuthToken:
        """Authenticate user and return tokens"""
        
        # Find user by email
        user_id = self.users_by_email.get(login.email)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = self.users.get(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not self.verify_password(login.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Get tenant
        tenant = self.tenants.get(user.tenant_id)
        if not tenant:
            raise HTTPException(status_code=500, detail="Tenant not found")
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        return self.generate_tokens(user, tenant)
    
    def generate_tokens(self, user: User, tenant: Tenant) -> AuthToken:
        """Generate JWT access and refresh tokens"""
        now = datetime.utcnow()
        
        # Get user permissions
        permissions = [perm.value for perm in ROLE_PERMISSIONS.get(user.role, [])]
        
        # Access token payload
        access_payload = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "role": user.role.value,
            "permissions": permissions,
            "subscription_plan": tenant.subscription_plan,
            "exp": now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
            "iat": now,
            "type": "access"
        }
        
        # Refresh token payload
        refresh_payload = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": now,
            "type": "refresh"
        }
        
        access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return AuthToken(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role.value
        )
    
    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user_permissions = ROLE_PERMISSIONS.get(user.role, [])
        return permission in user_permissions

# Global auth service instance
auth_service = AuthService()

# FastAPI security
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user"""
    token_payload = auth_service.verify_token(credentials.credentials)
    
    if token_payload.type != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    
    user = auth_service.get_user(token_payload.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user

async def get_current_tenant(user: User = Depends(get_current_user)) -> Tenant:
    """Get current user's tenant"""
    tenant = auth_service.get_tenant(user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=500, detail="Tenant not found")
    
    return tenant

def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def permission_checker(user: User = Depends(get_current_user)):
        if not auth_service.has_permission(user, permission):
            raise HTTPException(
                status_code=403, 
                detail=f"Permission required: {permission.value}"
            )
        return user
    return permission_checker

def require_role(required_role: Role):
    """Decorator to require specific role or higher"""
    def role_checker(user: User = Depends(get_current_user)):
        role_hierarchy = {
            Role.VIEWER: 1,
            Role.ENGINEER: 2, 
            Role.ADMIN: 3,
            Role.SUPER_ADMIN: 4
        }
        
        if role_hierarchy.get(user.role, 0) < role_hierarchy.get(required_role, 99):
            raise HTTPException(
                status_code=403,
                detail=f"Role required: {required_role.value}"
            )
        return user
    return role_checker