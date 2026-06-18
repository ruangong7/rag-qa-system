# Technical Specification — 技术规范 TS-2024-001

## 1. System Architecture Requirements / 系统架构要求

### 1.1 Microservice Architecture / 微服务架构
All new services must follow the microservice architecture pattern with the following constraints:
- Each service must have its own database (Database per Service pattern)
- Inter-service communication must use gRPC or asynchronous messaging (RabbitMQ/Kafka)
- Service discovery via Consul or Kubernetes DNS
- Circuit breaker pattern required for all external service calls (min 5 failures in 10s window)

所有新服务必须遵循微服务架构模式，约束条件如下：
- 每个服务必须拥有独立数据库（每服务一数据库模式）
- 服务间通信必须使用 gRPC 或异步消息（RabbitMQ / Kafka）
- 服务发现通过 Consul 或 Kubernetes DNS
- 所有外部服务调用必须实施熔断器模式（10 秒窗口内最少 5 次失败触发）

### 1.2 API Design Standards / API 设计标准
- RESTful APIs must follow OpenAPI 3.0 specification
- API versioning via URL path: `/api/v1/`, `/api/v2/`
- Rate limiting: 100 requests/minute per API key for standard tier
- All endpoints must return appropriate HTTP status codes and standardized error format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": []
  }
}
```

### 1.3 Database Standards / 数据库标准
- Primary database: PostgreSQL 15+ for relational data
- Search/analytics: Elasticsearch 8.x (not required for simple search — Qdrant acceptable for vector workloads)
- Cache: Redis 7.x with maxmemory-policy allkeys-lru
- All schemas must be version-controlled using Flyway or Liquibase

## 2. Security Requirements / 安全要求

### 2.1 Authentication & Authorization / 认证与授权
- OAuth 2.0 + OpenID Connect (OIDC) for user authentication
- JWT access tokens with 15-minute expiry, refresh tokens with 7-day expiry
- Role-Based Access Control (RBAC) with least privilege principle
- Service-to-service authentication via mTLS

### 2.2 Encryption Standards / 加密标准
- Data in transit: TLS 1.3 minimum
- Data at rest: AES-256-GCM
- Password hashing: bcrypt with cost factor ≥ 12
- API keys must be stored as SHA-256 hashes

### 2.3 Vulnerability Management / 漏洞管理
- All dependencies must be scanned with OWASP Dependency-Check or Snyk weekly
- Critical vulnerabilities must be patched within 48 hours
- High vulnerabilities must be patched within 7 days
- Regular penetration testing at least bi-annually

## 3. Performance Requirements / 性能要求

### 3.1 Response Time / 响应时间
| Endpoint Type | P50 | P95 | P99 |
|--------------|-----|-----|-----|
| Read (GET) | <100ms | <500ms | <1000ms |
| Write (POST/PUT) | <200ms | <1000ms | <2000ms |
| Search | <300ms | <1500ms | <3000ms |

### 3.2 Availability / 可用性
- Service availability target: 99.9% (8.76 hours downtime/year)
- Recovery Time Objective (RTO): < 1 hour
- Recovery Point Objective (RPO): < 5 minutes
- Multi-AZ deployment required for production services

### 3.3 Scalability / 可扩展性
- Services must support horizontal scaling (stateless design)
- Database connection pooling with max 100 connections per instance
- Autoscaling policy: CPU > 70% for 5 minutes → add 2 instances
