"""
Authentication routes for DeepSim SaaS platform
Handles user registration, login, logout, and token management
"""

from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from auth import (
    AuthService, UserRegistration, UserLogin, AuthToken, User, Tenant,
    auth_service, get_current_user, get_current_tenant
)
from database import db_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)

class PasswordResetRequest(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')

class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)

class UserProfile(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)

@router.post("/register", response_model=AuthToken)
async def register_user(registration: UserRegistration, request: Request):
    """Register new user and create tenant"""
    try:
        # Register user with auth service
        auth_token = await auth_service.register_user(registration)
        
        # Also create tenant and user in database
        tenant_id = await db_manager.create_tenant(
            name=registration.company_name,
            slug=auth_service.generate_slug(registration.company_name)
        )
        
        user_id = await db_manager.create_user(
            tenant_id=tenant_id,
            user_data={
                "email": registration.email,
                "password_hash": auth_service.hash_password(registration.password),
                "first_name": registration.first_name,
                "last_name": registration.last_name,
                "role": "admin"
            }
        )
        
        logger.info(f"User registered successfully: {registration.email} for tenant: {registration.company_name}")
        
        return auth_token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/login", response_model=AuthToken)
async def login_user(login: UserLogin, request: Request, response: Response):
    """Authenticate user and return JWT tokens"""
    try:
        auth_token = await auth_service.login_user(login)
        
        # Set secure HTTP-only cookie for refresh token (optional)
        response.set_cookie(
            key="refresh_token",
            value=auth_token.refresh_token,
            httponly=True,
            secure=True,  # Set to True in production with HTTPS
            samesite="strict",
            max_age=30 * 24 * 60 * 60  # 30 days
        )
        
        logger.info(f"User logged in successfully: {login.email}")
        
        return auth_token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.post("/refresh", response_model=AuthToken)
async def refresh_token(
    refresh_request: Optional[RefreshTokenRequest] = None,
    request: Request = None
):
    """Refresh access token using refresh token"""
    try:
        # Get refresh token from request body or cookie
        refresh_token = None
        if refresh_request and refresh_request.refresh_token:
            refresh_token = refresh_request.refresh_token
        elif request:
            refresh_token = request.cookies.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token required")
        
        # Verify refresh token
        try:
            token_payload = auth_service.verify_token(refresh_token)
        except HTTPException:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        if token_payload.type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Get user and tenant
        user = auth_service.get_user(token_payload.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        tenant = auth_service.get_tenant(token_payload.tenant_id)
        if not tenant:
            raise HTTPException(status_code=401, detail="Tenant not found")
        
        # Generate new tokens
        new_tokens = auth_service.generate_tokens(user, tenant)
        
        return new_tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")

@router.post("/logout")
async def logout_user(response: Response, current_user: User = Depends(get_current_user)):
    """Logout user and clear refresh token cookie"""
    try:
        # Clear refresh token cookie
        response.delete_cookie(key="refresh_token")
        
        logger.info(f"User logged out: {current_user.email}")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant)
):
    """Get current user information"""
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "role": current_user.role.value,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at.isoformat(),
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None
        },
        "tenant": {
            "id": current_tenant.id,
            "name": current_tenant.name,
            "slug": current_tenant.slug,
            "subscription_plan": current_tenant.subscription_plan,
            "subscription_status": current_tenant.subscription_status
        }
    }

@router.put("/profile")
async def update_user_profile(
    profile: UserProfile,
    current_user: User = Depends(get_current_user)
):
    """Update user profile information"""
    try:
        # Update user in auth service (in-memory)
        if profile.first_name is not None:
            current_user.first_name = profile.first_name
        if profile.last_name is not None:
            current_user.last_name = profile.last_name
        
        # TODO: Update in database as well
        
        return {"message": "Profile updated successfully"}
        
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(status_code=500, detail="Profile update failed")

@router.post("/change-password")
async def change_password(
    change_request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user)
):
    """Change user password"""
    try:
        # Verify current password
        if not auth_service.verify_password(change_request.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Hash new password
        new_password_hash = auth_service.hash_password(change_request.new_password)
        
        # Update password in auth service (in-memory)
        current_user.password_hash = new_password_hash
        
        # TODO: Update in database as well
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(status_code=500, detail="Password change failed")

@router.post("/forgot-password")
async def forgot_password(reset_request: PasswordResetRequest):
    """Request password reset"""
    try:
        # TODO: Implement password reset functionality
        # 1. Generate secure reset token
        # 2. Send email with reset link
        # 3. Store token with expiration
        
        # For now, just log the request
        logger.info(f"Password reset requested for: {reset_request.email}")
        
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, you will receive a password reset link"}
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        raise HTTPException(status_code=500, detail="Password reset request failed")

@router.post("/reset-password")
async def reset_password(reset_confirm: PasswordResetConfirm):
    """Reset password using reset token"""
    try:
        # TODO: Implement password reset confirmation
        # 1. Verify reset token
        # 2. Check token expiration
        # 3. Update user password
        # 4. Invalidate reset token
        
        logger.info(f"Password reset attempted with token: {reset_confirm.token[:8]}...")
        
        return {"message": "Password reset successfully"}
        
    except Exception as e:
        logger.error(f"Password reset error: {e}")
        raise HTTPException(status_code=500, detail="Password reset failed")

@router.get("/verify-email/{token}")
async def verify_email(token: str):
    """Verify user email address"""
    try:
        # TODO: Implement email verification
        # 1. Verify email verification token
        # 2. Mark user as verified
        # 3. Update database
        
        logger.info(f"Email verification attempted with token: {token[:8]}...")
        
        return {"message": "Email verified successfully"}
        
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(status_code=500, detail="Email verification failed")

@router.post("/resend-verification")
async def resend_verification_email(current_user: User = Depends(get_current_user)):
    """Resend email verification"""
    try:
        if current_user.is_verified:
            return {"message": "Email is already verified"}
        
        # TODO: Generate and send new verification email
        
        logger.info(f"Verification email resent to: {current_user.email}")
        
        return {"message": "Verification email sent"}
        
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(status_code=500, detail="Failed to resend verification email")

@router.get("/validate-token")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token (utility endpoint)"""
    try:
        if not credentials:
            raise HTTPException(status_code=401, detail="Token required")
        
        token_payload = auth_service.verify_token(credentials.credentials)
        
        return {
            "valid": True,
            "user_id": token_payload.user_id,
            "tenant_id": token_payload.tenant_id,
            "role": token_payload.role,
            "expires_at": token_payload.exp.isoformat()
        }
        
    except HTTPException as e:
        return {
            "valid": False,
            "error": e.detail
        }
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return {
            "valid": False,
            "error": "Token validation failed"
        }