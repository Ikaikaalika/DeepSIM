"""
Middleware for DeepSim SaaS platform
Handles tenant context, rate limiting, security headers, and request logging
"""

import time
import jwt
from typing import Optional
from urllib.parse import urlparse
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from auth import JWT_SECRET, JWT_ALGORITHM, auth_service
from database import db_manager

logger = logging.getLogger(__name__)

class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and set tenant context from:
    1. JWT token (primary method)
    2. Subdomain (secondary method)
    3. Custom header (for API access)
    """
    
    async def dispatch(self, request: Request, call_next):
        tenant_id = None
        tenant_slug = None
        
        try:
            # Method 1: Extract from JWT token (most secure)
            tenant_id = await self._extract_tenant_from_token(request)
            
            # Method 2: Extract from subdomain if no token
            if not tenant_id:
                tenant_id, tenant_slug = await self._extract_tenant_from_subdomain(request)
            
            # Method 3: Extract from custom header (for API access)
            if not tenant_id:
                tenant_id = await self._extract_tenant_from_header(request)
            
            # Set tenant context in request state
            request.state.tenant_id = tenant_id
            request.state.tenant_slug = tenant_slug
            
            # Skip tenant validation for public endpoints
            if self._is_public_endpoint(request.url.path):
                response = await call_next(request)
                return response
            
            # Validate tenant exists and is active
            if tenant_id:
                tenant = auth_service.get_tenant(tenant_id)
                if not tenant:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Invalid tenant", "code": "TENANT_NOT_FOUND"}
                    )
                
                if tenant.subscription_status not in ["active", "trialing"]:
                    return JSONResponse(
                        status_code=402,
                        content={
                            "error": "Subscription required", 
                            "code": "SUBSCRIPTION_INACTIVE",
                            "subscription_status": tenant.subscription_status
                        }
                    )
                
                request.state.tenant = tenant
            else:
                # Some endpoints require tenant context
                if self._requires_tenant_context(request.url.path):
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Tenant context required", "code": "NO_TENANT_CONTEXT"}
                    )
            
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Tenant context middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "code": "MIDDLEWARE_ERROR"}
            )
    
    async def _extract_tenant_from_token(self, request: Request) -> Optional[str]:
        """Extract tenant_id from JWT token"""
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        try:
            token = auth_header.replace("Bearer ", "")
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload.get("tenant_id")
        except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
            return None
    
    async def _extract_tenant_from_subdomain(self, request: Request) -> tuple[Optional[str], Optional[str]]:
        """Extract tenant from subdomain (e.g., acme.deepsim.com)"""
        host = request.headers.get("host", "")
        
        # Skip localhost and IP addresses
        if "localhost" in host or "127.0.0.1" in host:
            return None, None
        
        # Extract subdomain
        parts = host.split(".")
        if len(parts) >= 3:  # subdomain.domain.com
            subdomain = parts[0]
            
            # Skip common subdomains
            if subdomain in ["www", "api", "app"]:
                return None, None
            
            # Look up tenant by slug
            tenant = await self._get_tenant_by_slug(subdomain)
            if tenant:
                return tenant.get("id"), subdomain
        
        return None, None
    
    async def _extract_tenant_from_header(self, request: Request) -> Optional[str]:
        """Extract tenant from custom header (for API access)"""
        return request.headers.get("x-tenant-id")
    
    async def _get_tenant_by_slug(self, slug: str) -> Optional[dict]:
        """Get tenant by slug from database"""
        try:
            return await db_manager.get_tenant_by_slug(slug)
        except Exception as e:
            logger.error(f"Error getting tenant by slug {slug}: {e}")
            return None
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint doesn't require tenant context"""
        public_paths = [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/auth/register",
            "/auth/login",
            "/auth/refresh"
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)
    
    def _requires_tenant_context(self, path: str) -> bool:
        """Check if endpoint requires tenant context"""
        tenant_required_paths = [
            "/flowsheet",
            "/simulate",
            "/ai/chat",
            "/mcp/",
            "/analytics/",
            "/export/"
        ]
        
        return any(path.startswith(required_path) for required_path in tenant_required_paths)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.thundercompute.ai"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting based on tenant and subscription plan"""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_counts = {}  # In production, use Redis
        self.window_size = 3600  # 1 hour window
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for public endpoints
        if self._is_exempt_path(request.url.path):
            return await call_next(request)
        
        tenant_id = getattr(request.state, 'tenant_id', None)
        if not tenant_id:
            return await call_next(request)
        
        # Get tenant subscription plan
        tenant = getattr(request.state, 'tenant', None)
        if not tenant:
            return await call_next(request)
        
        # Check rate limit
        if await self._is_rate_limited(tenant_id, tenant.subscription_plan, request.url.path):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "retry_after": self.window_size
                }
            )
        
        return await call_next(request)
    
    async def _is_rate_limited(self, tenant_id: str, subscription_plan: str, path: str) -> bool:
        """Check if request should be rate limited"""
        current_time = int(time.time())
        window_start = current_time - self.window_size
        
        # Get rate limits based on subscription plan
        limits = self._get_rate_limits(subscription_plan)
        
        # Determine endpoint category
        endpoint_category = self._get_endpoint_category(path)
        limit = limits.get(endpoint_category, limits.get('default', 1000))
        
        # Count requests in current window
        key = f"{tenant_id}:{endpoint_category}:{window_start // self.window_size}"
        current_count = self.request_counts.get(key, 0)
        
        if current_count >= limit:
            return True
        
        # Increment counter
        self.request_counts[key] = current_count + 1
        
        # Clean old entries (simple cleanup)
        self._cleanup_old_entries(window_start)
        
        return False
    
    def _get_rate_limits(self, subscription_plan: str) -> dict:
        """Get rate limits based on subscription plan"""
        limits = {
            "free": {
                "api_calls": 100,
                "simulations": 10,
                "ai_queries": 20,
                "default": 100
            },
            "pro": {
                "api_calls": 10000,
                "simulations": 1000,
                "ai_queries": 500,
                "default": 1000
            },
            "enterprise": {
                "api_calls": 100000,
                "simulations": -1,  # Unlimited
                "ai_queries": 5000,
                "default": 10000
            }
        }
        
        return limits.get(subscription_plan, limits["free"])
    
    def _get_endpoint_category(self, path: str) -> str:
        """Categorize endpoint for rate limiting"""
        if "/simulate" in path:
            return "simulations"
        elif "/ai/chat" in path:
            return "ai_queries"
        else:
            return "api_calls"
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from rate limiting"""
        exempt_paths = ["/health", "/docs", "/openapi.json"]
        return any(path.startswith(exempt_path) for exempt_path in exempt_paths)
    
    def _cleanup_old_entries(self, window_start: int):
        """Remove old rate limit entries"""
        keys_to_remove = []
        for key in self.request_counts:
            # Extract timestamp from key
            try:
                key_time = int(key.split(':')[-1]) * self.window_size
                if key_time < window_start:
                    keys_to_remove.append(key)
            except (ValueError, IndexError):
                continue
        
        for key in keys_to_remove:
            del self.request_counts[key]

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for monitoring and analytics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract request info
        tenant_id = getattr(request.state, 'tenant_id', 'unknown')
        user_agent = request.headers.get('user-agent', 'unknown')
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log request
            logger.info(
                f"REQUEST: {request.method} {request.url.path} | "
                f"Status: {response.status_code} | "
                f"Time: {process_time:.3f}s | "
                f"Tenant: {tenant_id} | "
                f"UserAgent: {user_agent[:50]}"
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"ERROR: {request.method} {request.url.path} | "
                f"Error: {str(e)} | "
                f"Time: {process_time:.3f}s | "
                f"Tenant: {tenant_id}"
            )
            raise

class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware with tenant-aware origins"""
    
    def __init__(self, app):
        super().__init__(app)
        self.allowed_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://*.deepsim.com",  # Wildcard for subdomains
        ]
    
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        origin = request.headers.get("origin")
        
        # Check if origin is allowed
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Origin, Content-Type, Accept, Authorization, X-Tenant-ID"
            )
        
        return response
    
    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is in allowed list"""
        if not origin:
            return False
        
        for allowed in self.allowed_origins:
            if allowed == origin:
                return True
            # Handle wildcard subdomains
            if "*." in allowed:
                domain = allowed.replace("*.", "")
                if origin.endswith(domain):
                    return True
        
        return False