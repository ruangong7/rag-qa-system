# Architecture Documentation — 架构文档 AD-2024

## Overview / 概述
This document describes the system architecture for the Enterprise Knowledge Management Platform (EKMP).
本文档描述企业知识管理平台 (EKMP) 的系统架构。

## 1. High-Level Architecture / 高层架构

```
┌─────────────────────────────────────────────────────────┐
│                     API Gateway (Kong)                    │
│              Rate Limiting / Auth / Routing              │
└──────┬──────────┬──────────┬──────────┬─────────────────┘
       │          │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
  │ User   │ │Search  │ │Doc     │ │Notifi- │
  │ Service│ │Service │ │Service │ │cation  │
  └────┬───┘ └───┬────┘ └───┬────┘ └───┬────┘
       │         │          │          │
  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
  │PostgreSQL││Qdrant  │ │  MinIO │ │ Redis  │
  └─────────┘ └────────┘ └────────┘ └────────┘
```

### 1.1 Service Boundary Definitions / 服务边界定义

**User Service (用户服务):**
- Manages user accounts, authentication, and RBAC permissions
- Owns the user database (PostgreSQL)
- Exposes gRPC interface for other services to verify tokens and permissions

**Search Service (搜索服务):**
- Provides full-text and vector search across all document types
- Uses Qdrant for vector embeddings and BM25 for keyword search
- Implements hybrid search with Reciprocal Rank Fusion
- Supports both Chinese and English queries natively

**Document Service (文档服务):**
- Handles document ingestion, versioning, and lifecycle management
- Stores raw documents in MinIO (S3-compatible object storage)
- Extracts text and metadata for indexing by Search Service
- Supports PDF, Markdown, Word, and scanned documents via OCR

**Notification Service (通知服务):**
- Sends email, in-app, and webhook notifications
- Implements retry with exponential backoff (max 5 retries)
- Rate-limited to 100 notifications/second per tenant

### 1.2 Message Queue Topology / 消息队列拓扑

All services communicate asynchronously through RabbitMQ with the following exchanges:

| Exchange | Type | Routing Key Pattern | Consumers |
|----------|------|---------------------|-----------|
| doc.events | topic | doc.created.# | Search, Notification |
| doc.events | topic | doc.updated.# | Search |
| doc.events | topic | doc.deleted.# | Search |
| user.events | topic | user.*.changed | All services |
| system.audit | fanout | - | Audit Logger |

## 2. Data Flow / 数据流

### 2.1 Document Ingestion Flow / 文档入库流程
1. User uploads document via API Gateway → Document Service
2. Document Service stores raw file in MinIO
3. Document Service publishes `doc.created` event to RabbitMQ
4. Search Service consumes event, downloads file from MinIO
5. Search Service performs text extraction, chunking, and embedding
6. Search Service indexes chunks into Qdrant
7. Search Service publishes `doc.indexed` event
8. Notification Service notifies user of completion

### 2.2 Query Flow / 查询流程
1. User submits query via API Gateway → Search Service
2. Search Service rewrites query (resolves co-reference from conversation history)
3. Search Service performs hybrid retrieval (dense + sparse + RRF)
4. Retrieved chunks are re-ranked using cross-encoder
5. LLM generates answer with citations
6. Response returned to user

## 3. Deployment Architecture / 部署架构

### 3.1 Kubernetes Deployment / K8s 部署
- All services deployed on Kubernetes 1.29+
- Minimum 3 replicas per service for high availability
- Pod anti-affinity rules to ensure distribution across nodes
- Resource requests and limits defined per service:

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| API Gateway | 500m | 2000m | 512Mi | 2Gi |
| User Service | 250m | 1000m | 256Mi | 1Gi |
| Search Service | 1000m | 4000m | 2Gi | 8Gi |
| Document Service | 500m | 2000m | 512Mi | 2Gi |
| Notification | 250m | 500m | 256Mi | 512Mi |

### 3.2 Monitoring Stack / 监控栈
- Metrics: Prometheus + Grafana
- Logging: structlog (JSON) → Filebeat → Elasticsearch → Kibana
- Tracing: OpenTelemetry → Jaeger
- Alerting: Alertmanager → PagerDuty / WeChat Work
