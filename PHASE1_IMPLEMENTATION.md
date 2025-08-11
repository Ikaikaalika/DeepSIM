# DeepSim SaaS Phase 1 Implementation

## 🎯 Overview

Phase 1 transforms DeepSim from a development prototype into a multi-tenant SaaS platform with enterprise-grade authentication, security, and database architecture.

## ✅ Completed Features

### 1. Authentication & User Management (`auth.py`, `auth_routes.py`)
- **JWT-based authentication** with access and refresh tokens
- **User registration** with automatic tenant creation
- **Role-based access control (RBAC)** with 4 roles:
  - Viewer: Read-only access to flowsheets
  - Engineer: Create and run simulations
  - Admin: Full tenant management
  - Super Admin: Cross-tenant access
- **Password security** with bcrypt hashing
- **Token refresh** mechanism for seamless user experience

### 2. Multi-Tenancy Architecture (`database.py`)
- **PostgreSQL database** with automatic tenant isolation
- **Row Level Security (RLS)** ensures data separation
- **Tenant-aware database operations** with context management
- **Scalable schema** supporting unlimited tenants
- **Foreign key relationships** maintaining data integrity

### 3. Security & Middleware (`middleware.py`)
- **Tenant Context Middleware**: Automatic tenant extraction from JWT/subdomain
- **Security Headers**: OWASP-compliant HTTP security headers
- **Rate Limiting**: Subscription-based API throttling
- **Request Logging**: Comprehensive audit trails
- **CORS Protection**: Secure cross-origin resource sharing

### 4. Database Schema
```sql
-- Core Tables Created:
├── tenants (id, name, slug, subscription_plan, settings)
├── users (id, tenant_id, email, role, password_hash)
├── flowsheets (id, tenant_id, user_id, name, data)
├── simulations (id, tenant_id, flowsheet_id, results)
├── conversations (id, tenant_id, user_id, context_data)
├── conversation_turns (id, tenant_id, user_message, ai_response)
└── feedback (id, tenant_id, turn_id, rating, text_feedback)
```

### 5. Enhanced Main Application (`main.py`)
- **Integrated middleware stack** for security and tenant isolation  
- **Protected endpoints** with permission-based access control
- **Comprehensive health checks** showing all service statuses
- **Database integration** with tenant-aware operations
- **Backward compatibility** with existing simulation features

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
pip install -r requirements_saas.txt
```

### 2. Setup Database
```bash
# Install PostgreSQL
brew install postgresql  # macOS
# or use Docker:
docker run --name deepsim-db -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15

# Create database
createdb deepsim_saas

# Initialize tables
python init_db.py
```

### 3. Start the Server
```bash
python main.py
```

## 🔐 API Endpoints

### Authentication
```
POST /auth/register     # Register new user and tenant
POST /auth/login        # User login
POST /auth/refresh      # Refresh access token
POST /auth/logout       # User logout
GET  /auth/me          # Get current user info
PUT  /auth/profile     # Update user profile
```

### Protected Flowsheet Operations
```
POST /flowsheet                    # Create flowsheet (requires CREATE_FLOWSHEETS)
GET  /flowsheet/{id}              # View flowsheet (requires VIEW_FLOWSHEETS)  
PUT  /flowsheet/{id}              # Edit flowsheet (requires EDIT_FLOWSHEETS)
DELETE /flowsheet/{id}            # Delete flowsheet (requires DELETE_FLOWSHEETS)
POST /simulate                    # Run simulation (requires RUN_SIMULATIONS)
```

### System
```
GET  /health           # Comprehensive health check
GET  /                 # API information
```

## 🔑 Authentication Flow

### 1. User Registration
```json
POST /auth/register
{
  "email": "user@company.com",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe", 
  "company_name": "Acme Chemical Co"
}
```
**Response**: JWT tokens + user/tenant info

### 2. Login
```json
POST /auth/login
{
  "email": "user@company.com",
  "password": "SecurePass123"
}
```
**Response**: JWT access token (24h) + refresh token (30d)

### 3. Authenticated Requests
```bash
curl -H "Authorization: Bearer <access_token>" \
     http://localhost:8000/flowsheet
```

## 🏢 Multi-Tenancy

### Tenant Isolation Methods
1. **JWT Token** (Primary): `{"tenant_id": "uuid", "user_id": "uuid"}`
2. **Subdomain**: `acme.deepsim.com` → tenant slug "acme"  
3. **Header**: `X-Tenant-ID: uuid`

### Database Isolation
- **Row Level Security (RLS)** automatically filters data by tenant
- **Tenant context** set via `current_setting('app.current_tenant_id')`
- **Zero data leakage** between tenants guaranteed at database level

### Rate Limiting by Plan
```javascript
{
  "free": { "api_calls": 100, "simulations": 10 },
  "pro": { "api_calls": 10000, "simulations": 1000 },
  "enterprise": { "api_calls": 100000, "simulations": -1 }
}
```

## 🛡️ Security Features

### Password Security
- **Minimum 8 characters** with complexity requirements
- **bcrypt hashing** with salt for password storage
- **No plaintext passwords** anywhere in the system

### JWT Token Security
- **HS256 signing** with secure secret key
- **Short-lived access tokens** (24 hours)
- **Long-lived refresh tokens** (30 days)
- **Token validation** on every protected request

### HTTP Security Headers
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
Content-Security-Policy: default-src 'self'
```

## 📊 Monitoring & Logging

### Request Logging
Every request logs:
- HTTP method, path, status code
- Response time and tenant ID
- User agent and error details
- Processing time in response headers

### Health Monitoring
```json
GET /health
{
  "status": "healthy",
  "saas_version": "2.0.0",
  "services": {
    "database": "online",
    "authentication": "online", 
    "multi_tenancy": "online",
    "rate_limiting": "online"
  },
  "features": {
    "tenant_isolation": true,
    "jwt_authentication": true,
    "rbac": true,
    "api_rate_limiting": true
  }
}
```

## 🔧 Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://deepsim:password@localhost:5432/deepsim_saas

# Security
JWT_SECRET=your-super-secret-jwt-key-change-in-production

# Thunder Compute (AI)
THUNDER_API_KEY=your_thunder_compute_key
USE_MCP=true
```

## 📈 Performance Optimizations

### Database
- **Connection pooling** with 10 base + 20 overflow connections
- **Prepared statements** for common queries
- **Indexes** on all foreign keys and lookup columns
- **Row Level Security** with minimal overhead

### Caching
- **In-memory rate limiting** (Redis in production)
- **Database query optimization** with SQLAlchemy
- **Session management** with secure cookies

## 🧪 Testing

### Basic Health Check
```bash
curl http://localhost:8000/health
```

### Register Test User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123",
    "first_name": "Test", 
    "last_name": "User",
    "company_name": "Test Company"
  }'
```

### Create Protected Flowsheet
```bash
# First login to get token
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123"}' \
  | jq -r '.access_token')

# Create flowsheet with authentication  
curl -X POST http://localhost:8000/flowsheet \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Process", "description": "My first flowsheet"}'
```

## 🔮 What's Next?

Phase 1 provides the foundation. Next phases will add:

### Phase 2 - Monetization
- Stripe integration for payments
- Subscription management
- Usage tracking and billing

### Phase 3 - Operations  
- Admin dashboard
- Customer support system
- Analytics and reporting

### Phase 4 - Enterprise
- Advanced security compliance (SOC2)
- SSO integration
- Custom deployment options

## 🏗️ Architecture Summary

```
┌─────────────────────────────────────────────┐
│           DeepSim SaaS v2.0                │
├─────────────────────────────────────────────┤
│  Security Headers → Rate Limiting           │
│      ↓                  ↓                   │
│  Tenant Context → Request Logging           │
├─────────────────────────────────────────────┤
│  JWT Authentication → RBAC Authorization    │
├─────────────────────────────────────────────┤
│  Multi-Tenant Database (PostgreSQL + RLS)   │
├─────────────────────────────────────────────┤
│  Original DeepSim Features (MCP + AI)       │
└─────────────────────────────────────────────┘
```

The Phase 1 implementation successfully transforms DeepSim into an enterprise-ready SaaS platform while maintaining all original functionality and adding comprehensive security, authentication, and multi-tenancy capabilities.