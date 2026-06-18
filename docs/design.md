# Design Notes — RAG QA System

## 关键选择与权衡

**1. BGE-M3 作为统一 Embedding 模型**
选择原因：原生支持中英双语，单一模型同时产出 Dense (1024d) 和 Sparse 向量，无需分别部署 dense 和 BM25 模型。代价是模型较大（~2GB），冷启动约 2 秒。

**2. Qdrant 替代 Elasticsearch**
Qdrant 支持向量搜索 + 内置 BM25 稀疏索引，单二进制部署，运维成本远低于 ES。局限性：全文检索功能不如 ES 丰富，对复杂 query DSL 支持有限。当前场景（内部文档搜索）足够。

**3. RRF 融合替代加权求和**
Dense 和 Sparse 的分数量纲差异大（cosine ∈ [-1,1] vs BM25 无界），直接加权需调参且不稳定。RRF 只依赖排序位置，不需要分数归一化，实践更稳定。

**4. Cross-encoder Reranker 的必要性**
初召 top-20 中可能包含语义相关但不精确的 chunk，Reranker 逐对精排后 top-5 质量显著提升。代价是额外 200-300ms 延迟，但仍在 10s 预算内。

**5. 结构日志选型 structlog**
相比 print/标准 logging，structlog 产出 JSON 行，可直接消费到 ELK/Grafana，支持按 request_id、session_id 追踪全链路。零额外依赖。

## 可发展性

- 文档扩展：ingestion pipeline 支持增量索引，通过 chunk_hash 去重
- 检索策略调整：config.yaml 集中管理参数，无需改代码
- 质量迭代：eval/evaluate.py 自动化评估，每次变更后可对比指标
- 日志增强：协议化 stage 字段，可插拔增加 tracing（OpenTelemetry）
