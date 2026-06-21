# Architecture Documentation AD-2024

## Overview

This document describes the system architecture for the Enterprise Knowledge Management Platform (EKMP), including core services, supporting infrastructure, data flow, and deployment guidance.

## 1. High-Level Architecture

The platform consists of the following major layers and components:

- API Gateway for ingress, authentication checks, rate limiting, and routing
- User Service for identity, RBAC, and user lifecycle
- Search Service for hybrid retrieval and evidence-grounded query handling
- Document Service for ingestion, extraction, and lifecycle management
- Notification Service for email, webhook, and in-app delivery

### Supporting Stack

The main supporting technologies in the architecture stack are:

- PostgreSQL for relational application data
- ChromaDB for vector storage and semantic retrieval
- MinIO for object storage and raw document persistence
- Redis for cache and session-oriented acceleration
- RabbitMQ for asynchronous event delivery between services

### 1.1 Service Boundaries

**User Service**

- Manages user accounts, authentication, and RBAC permissions
- Owns the user database in PostgreSQL
- Exposes internal interfaces for token and permission verification

**Search Service**

- Provides full-text and vector search across indexed knowledge assets
- Executes hybrid retrieval using dense recall, sparse recall, and Reciprocal Rank Fusion (RRF)
- Re-ranks candidates for answer generation and evidence grounding
- Returns traceable contexts for citation-backed responses
- Supports both Chinese and English queries

**Document Service**

- Handles document ingestion, versioning, and lifecycle management
- Stores raw files in MinIO
- Extracts text and metadata for downstream indexing
- Supports Markdown, text, PDF, and OCR-derived inputs

**Notification Service**

- Sends email, in-app, and webhook notifications
- Supports retry with bounded backoff
- Delivers indexing and workflow status updates

### 1.2 Message Queue Topology

Services communicate asynchronously through RabbitMQ for document and workflow events.

Representative patterns include:

- `doc.created` for new document ingestion
- `doc.updated` for re-index and refresh workflows
- `doc.deleted` for index cleanup
- `system.audit` for fan-out style audit events

## 2. Data Flow

### 2.1 Document Ingestion Flow

1. A user uploads a document through the API Gateway to the Document Service.
2. The Document Service stores the raw file in MinIO.
3. A document event is published to RabbitMQ.
4. The Search Service consumes the event and fetches the file.
5. The Search Service performs extraction, chunking, metadata normalization, and embedding.
6. Chunks are indexed into ChromaDB and synchronized with the sparse retrieval index.
7. Completion status is emitted for downstream notification handling.

### 2.2 Query Flow

1. A user submits a query through the API Gateway to the Search Service.
2. The Search Service may rewrite the query using recent conversation context.
3. The Search Service performs hybrid retrieval with dense search, sparse search, and RRF fusion.
4. Top candidates may be re-ranked before answer generation.
5. The LLM generates an answer strictly grounded in retrieved evidence.
6. The response returns with citations and request telemetry.

## 3. Deployment Architecture

### 3.1 Kubernetes Deployment

- All services are designed for containerized deployment
- Horizontal scaling is applied to stateless services
- Anti-affinity and readiness checks are used for service resilience
- Search workloads require higher CPU and memory allocation than standard control-plane services

### 3.2 Observability Stack

- Metrics: Prometheus + Grafana
- Logging: structured JSON logs shipped to a log aggregation pipeline
- Tracing: OpenTelemetry-compatible distributed tracing
- Alerting: threshold and latency based operational alerts

## 4. Operational Notes

- ChromaDB and sparse retrieval artifacts must remain aligned after re-indexing
- Search quality should be monitored alongside latency and citation validity
- Architecture guidance should stay consistent with the actual local demo stack and must not reference retired vector backends
