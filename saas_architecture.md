# DeepSim SaaS Architecture Design

## 🏗️ Multi-Tenant SaaS Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DeepSim SaaS Platform                       │
├─────────────────────────────────────────────────────────────────┤
│  Frontend Layer                                                │
│  ├── React Dashboard (Multi-tenant aware)                     │
│  ├── Process Designer (Tenant-isolated workspaces)            │
│  ├── AI Chat Interface (Per-tenant context)                   │
│  └── Admin Panel (Super admin + tenant admin)                 │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway                                                   │
│  ├── Authentication/Authorization                              │
│  ├── Rate Limiting (Per tenant/plan)                          │
│  ├── Request Routing                                           │
│  └── API Versioning                                            │
├─────────────────────────────────────────────────────────────────┤
│  Application Services                                          │
│  ├── Auth Service (Users, Tenants, Permissions)              │
│  ├── Billing Service (Subscriptions, Usage tracking)         │
│  ├── Process Service (Flowsheets, Simulations)               │
│  ├── AI Service (MCP Server, Model management)               │
│  └── Analytics Service (Usage, Performance metrics)          │
├─────────────────────────────────────────────────────────────────┤
│  Data Layer                                                    │
│  ├── PostgreSQL (Multi-tenant with tenant_id)                │
│  ├── Redis (Session, cache, rate limiting)                   │
│  ├── S3/MinIO (File storage, backups)                        │
│  └── ClickHouse (Analytics, time-series data)                │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure                                               │
│  ├── Kubernetes (Container orchestration)                     │
│  ├── Istio (Service mesh, security)                          │
│  ├── Prometheus/Grafana (Monitoring)                         │
│  └── ELK Stack (Logging)                                     │
└─────────────────────────────────────────────────────────────────┘
```

## 🔐 Authentication & Authorization

### JWT-Based Authentication
```python
# Enhanced auth system
class AuthService:
    def authenticate_user(self, email: str, password: str) -> AuthToken:
        # Multi-tenant user authentication
        user = self.user_repo.find_by_email_and_tenant(email, tenant_id)
        if user and verify_password(password, user.password_hash):
            return self.generate_jwt_token(user)
    
    def generate_jwt_token(self, user: User) -> AuthToken:
        payload = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "role": user.role,
            "permissions": user.get_permissions(),
            "subscription_plan": user.tenant.subscription_plan,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
```

### Role-Based Access Control
```python
class Permission(Enum):
    VIEW_FLOWSHEETS = "view_flowsheets"
    CREATE_FLOWSHEETS = "create_flowsheets"
    RUN_SIMULATIONS = "run_simulations"
    MANAGE_TEAM = "manage_team"
    VIEW_ANALYTICS = "view_analytics"
    ADMIN_TENANT = "admin_tenant"

class Role(Enum):
    VIEWER = "viewer"
    ENGINEER = "engineer"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

ROLE_PERMISSIONS = {
    Role.VIEWER: [Permission.VIEW_FLOWSHEETS],
    Role.ENGINEER: [Permission.VIEW_FLOWSHEETS, Permission.CREATE_FLOWSHEETS, Permission.RUN_SIMULATIONS],
    Role.ADMIN: [Permission.VIEW_FLOWSHEETS, Permission.CREATE_FLOWSHEETS, Permission.RUN_SIMULATIONS, Permission.MANAGE_TEAM, Permission.VIEW_ANALYTICS],
    Role.SUPER_ADMIN: [*Permission]  # All permissions
}
```

## 🏢 Multi-Tenancy Implementation

### Database Schema with Tenant Isolation
```sql
-- Core tenant table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    subscription_plan VARCHAR(50) NOT NULL DEFAULT 'free',
    subscription_status VARCHAR(20) NOT NULL DEFAULT 'active',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Multi-tenant aware tables
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'engineer',
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(tenant_id, email)
);

CREATE TABLE flowsheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Row Level Security (RLS) for automatic tenant isolation
ALTER TABLE flowsheets ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON flowsheets
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### Tenant Context Middleware
```python
class TenantContextMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extract tenant from JWT token or subdomain
        tenant_id = self.extract_tenant_id(request)
        
        if tenant_id:
            # Set tenant context for database queries
            async with database.transaction():
                await database.execute(
                    "SET LOCAL app.current_tenant_id = :tenant_id",
                    {"tenant_id": tenant_id}
                )
                request.state.tenant_id = tenant_id
                return await call_next(request)
        else:
            raise HTTPException(status_code=403, detail="Invalid tenant")
    
    def extract_tenant_id(self, request: Request) -> Optional[str]:
        # Method 1: From JWT token
        token = request.headers.get("Authorization")
        if token:
            payload = jwt.decode(token.replace("Bearer ", ""), JWT_SECRET)
            return payload.get("tenant_id")
        
        # Method 2: From subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            tenant = self.tenant_repo.find_by_slug(subdomain)
            return tenant.id if tenant else None
        
        return None
```

## 💳 Subscription & Billing System

### Subscription Plans
```python
@dataclass
class SubscriptionPlan:
    id: str
    name: str
    price_monthly: float
    price_annual: float
    features: Dict[str, Any]
    limits: Dict[str, int]

SUBSCRIPTION_PLANS = {
    "free": SubscriptionPlan(
        id="free",
        name="Free",
        price_monthly=0,
        price_annual=0,
        features={
            "simulations_per_month": 10,
            "api_calls_per_month": 100,
            "storage_gb": 1,
            "support": "community",
            "ai_assistance": True,
            "advanced_units": False
        },
        limits={
            "max_flowsheets": 5,
            "max_team_members": 1,
            "simulation_hours": 2
        }
    ),
    "pro": SubscriptionPlan(
        id="pro",
        name="Professional",
        price_monthly=99,
        price_annual=990,  # 2 months free
        features={
            "simulations_per_month": 1000,
            "api_calls_per_month": 10000,
            "storage_gb": 50,
            "support": "email",
            "ai_assistance": True,
            "advanced_units": True,
            "custom_components": True,
            "export_formats": ["json", "csv", "xlsx", "aspen"]
        },
        limits={
            "max_flowsheets": 100,
            "max_team_members": 10,
            "simulation_hours": 100
        }
    ),
    "enterprise": SubscriptionPlan(
        id="enterprise",
        name="Enterprise",
        price_monthly=499,
        price_annual=4990,
        features={
            "simulations_per_month": -1,  # Unlimited
            "api_calls_per_month": -1,
            "storage_gb": 500,
            "support": "priority",
            "ai_assistance": True,
            "advanced_units": True,
            "custom_components": True,
            "sso": True,
            "custom_integrations": True,
            "dedicated_support": True,
            "sla": "99.9%"
        },
        limits={
            "max_flowsheets": -1,
            "max_team_members": 100,
            "simulation_hours": -1
        }
    )
}
```

### Usage Tracking & Billing
```python
class UsageTracker:
    async def track_simulation(self, tenant_id: str, duration_seconds: int, 
                             complexity_score: float):
        usage = UsageRecord(
            tenant_id=tenant_id,
            event_type="simulation",
            quantity=duration_seconds,
            metadata={
                "complexity_score": complexity_score,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.usage_repo.save(usage)
        
        # Check limits
        await self.check_usage_limits(tenant_id)
    
    async def check_usage_limits(self, tenant_id: str):
        tenant = await self.tenant_repo.get(tenant_id)
        plan = SUBSCRIPTION_PLANS[tenant.subscription_plan]
        
        current_usage = await self.get_monthly_usage(tenant_id)
        
        if plan.features["simulations_per_month"] > 0:  # -1 means unlimited
            if current_usage.simulations >= plan.features["simulations_per_month"]:
                raise UsageLimitExceeded("Monthly simulation limit reached")

class BillingService:
    async def process_monthly_billing(self):
        for tenant in await self.get_active_subscriptions():
            usage = await self.usage_tracker.get_monthly_usage(tenant.id)
            invoice = await self.generate_invoice(tenant, usage)
            await self.stripe_client.create_invoice(invoice)
```

## ⚡ Performance & Scalability

### Database Sharding Strategy
```python
# Shard by tenant_id for horizontal scaling
class TenantAwareDatabase:
    def __init__(self):
        self.shards = {
            "shard_1": create_engine("postgresql://...shard1"),
            "shard_2": create_engine("postgresql://...shard2"),
            "shard_3": create_engine("postgresql://...shard3"),
        }
    
    def get_shard_for_tenant(self, tenant_id: str) -> str:
        # Consistent hashing for tenant distribution
        hash_value = int(hashlib.md5(tenant_id.encode()).hexdigest(), 16)
        shard_index = hash_value % len(self.shards)
        return f"shard_{shard_index + 1}"
    
    async def execute_query(self, tenant_id: str, query: str, params: dict):
        shard_name = self.get_shard_for_tenant(tenant_id)
        engine = self.shards[shard_name]
        return await engine.execute(query, params)
```

### Redis-Based Caching
```python
class CacheService:
    def __init__(self):
        self.redis = Redis.from_url("redis://redis-cluster:6379")
    
    async def cache_simulation_result(self, tenant_id: str, 
                                    flowsheet_hash: str, result: dict):
        key = f"sim:{tenant_id}:{flowsheet_hash}"
        await self.redis.setex(key, 3600, json.dumps(result))  # 1 hour TTL
    
    async def get_cached_result(self, tenant_id: str, 
                              flowsheet_hash: str) -> Optional[dict]:
        key = f"sim:{tenant_id}:{flowsheet_hash}"
        result = await self.redis.get(key)
        return json.loads(result) if result else None
```

## 🔒 Security Implementation

### API Rate Limiting
```python
class RateLimiter:
    def __init__(self):
        self.redis = Redis.from_url("redis://redis-cluster:6379")
    
    async def check_rate_limit(self, tenant_id: str, endpoint: str) -> bool:
        tenant = await self.tenant_repo.get(tenant_id)
        plan = SUBSCRIPTION_PLANS[tenant.subscription_plan]
        
        # Different limits based on subscription plan
        limits = {
            "free": {"api_calls": 100, "simulations": 10},
            "pro": {"api_calls": 10000, "simulations": 1000},
            "enterprise": {"api_calls": 100000, "simulations": -1}
        }
        
        limit = limits[tenant.subscription_plan]["api_calls"]
        if limit == -1:  # Unlimited
            return True
        
        key = f"rate_limit:{tenant_id}:{endpoint}:{datetime.now().strftime('%Y%m%d%H')}"
        current = await self.redis.incr(key)
        
        if current == 1:
            await self.redis.expire(key, 3600)  # 1 hour window
        
        return current <= limit
```

### Data Encryption
```python
class EncryptionService:
    def __init__(self):
        self.fernet = Fernet(ENCRYPTION_KEY.encode())
    
    def encrypt_sensitive_data(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        return self.fernet.decrypt(encrypted_data.encode()).decode()

# Database field encryption
class EncryptedField:
    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.encryption.encrypt_sensitive_data(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return self.encryption.decrypt_sensitive_data(value)
        return value
```

## 📊 Analytics & Monitoring

### Business Metrics Collection
```python
class AnalyticsService:
    async def track_event(self, tenant_id: str, user_id: str, 
                         event: str, properties: dict):
        event_record = AnalyticsEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event,
            properties=properties,
            timestamp=datetime.utcnow()
        )
        
        # Write to ClickHouse for fast analytics queries
        await self.clickhouse_client.insert("events", event_record.dict())
        
        # Also send to real-time analytics
        await self.kafka_producer.send("analytics_events", event_record.dict())
    
    async def get_usage_analytics(self, tenant_id: str, 
                                date_range: tuple) -> dict:
        query = """
        SELECT 
            date(timestamp) as date,
            count(*) as events,
            countIf(event_type = 'simulation_run') as simulations,
            countIf(event_type = 'ai_query') as ai_queries,
            avg(properties['execution_time']) as avg_response_time
        FROM events 
        WHERE tenant_id = :tenant_id 
        AND timestamp BETWEEN :start_date AND :end_date
        GROUP BY date
        ORDER BY date
        """
        
        return await self.clickhouse_client.execute(
            query, 
            {"tenant_id": tenant_id, "start_date": date_range[0], "end_date": date_range[1]}
        )
```

## 🚀 Deployment Architecture

### Kubernetes Manifests
```yaml
# deepsim-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deepsim-production

---
# deepsim-api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deepsim-api
  namespace: deepsim-production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: deepsim-api
  template:
    metadata:
      labels:
        app: deepsim-api
    spec:
      containers:
      - name: api
        image: deepsim/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: deepsim-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: deepsim-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# deepsim-mcp-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: deepsim-mcp
  namespace: deepsim-production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: deepsim-mcp
  template:
    metadata:
      labels:
        app: deepsim-mcp
    spec:
      containers:
      - name: mcp-server
        image: deepsim/mcp-server:latest
        ports:
        - containerPort: 8001
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

---
# deepsim-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: deepsim-api-hpa
  namespace: deepsim-production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: deepsim-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Terraform Infrastructure
```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# EKS Cluster
resource "aws_eks_cluster" "deepsim" {
  name     = "deepsim-production"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = "1.27"

  vpc_config {
    subnet_ids = [
      aws_subnet.private_1.id,
      aws_subnet.private_2.id,
      aws_subnet.public_1.id,
      aws_subnet.public_2.id
    ]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]
}

# RDS PostgreSQL for multi-tenant data
resource "aws_db_instance" "deepsim_db" {
  identifier = "deepsim-production"
  
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.r6g.large"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_encrypted     = true
  
  db_name  = "deepsim"
  username = "deepsim"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.deepsim.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "deepsim-production-final-snapshot"
}

# ElastiCache Redis for caching and sessions
resource "aws_elasticache_replication_group" "deepsim" {
  replication_group_id       = "deepsim-redis"
  description                = "DeepSim Redis cluster"
  
  node_type                  = "cache.r6g.large"
  port                       = 6379
  parameter_group_name       = "default.redis7"
  
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  subnet_group_name = aws_elasticache_subnet_group.deepsim.name
  security_group_ids = [aws_security_group.redis.id]
}
```

This SaaS architecture provides:
- **Enterprise-grade security** with tenant isolation
- **Scalable infrastructure** supporting thousands of tenants  
- **Flexible billing** with usage tracking and plan management
- **Comprehensive monitoring** for operations and business metrics
- **Cloud-native deployment** with Kubernetes and auto-scaling

The architecture is designed to support the transition from prototype to production SaaS platform serving chemical engineering companies worldwide.