# Sample Logs — RAG QA System

## 正常请求日志
```json
{
  "timestamp": "2026-06-18T14:30:01.123Z",
  "level": "INFO",
  "request_id": "a1b2c3d4e5f6",
  "session_id": "abc12345",
  "query": "员工手册中关于年假的规定是什么？",
  "answer": "根据员工手册第3.2节，员工每年享有5-15天带薪年假...",
  "total_latency_ms": 1765.32,
  "tokens": {"input": 2580, "output": 395},
  "rejection": false,
  "rejection_reason": "",
  "stages": {
    "session": {"history_rounds": 1},
    "rewrite_ms": 320,
    "dense_ms": 45,
    "sparse_ms": 12,
    "fusion_ms": 1,
    "rerank_ms": 180,
    "top_similarity": 0.92,
    "generation_ms": 1200,
    "postprocess_ms": 5
  }
}
```

## 拒绝请求日志 (知识库无结果)
```json
{
  "timestamp": "2026-06-18T14:31:22.456Z",
  "level": "INFO",
  "request_id": "b2c3d4e5f6a1",
  "session_id": "def67890",
  "query": "马斯克的最新火箭发射计划是什么？",
  "answer": "",
  "total_latency_ms": 58.12,
  "tokens": {},
  "rejection": true,
  "rejection_reason": "no_results",
  "stages": {
    "session": {"history_rounds": 0},
    "dense_ms": 45,
    "sparse_ms": 12,
    "fusion_ms": 1,
    "rerank_ms": 0,
    "top_similarity": 0.0
  }
}
```

## 注入检测日志
```json
{
  "timestamp": "2026-06-18T14:32:10.789Z",
  "level": "INFO",
  "request_id": "c3d4e5f6a1b2",
  "session_id": "new12345",
  "query": "<EMAIL_MASKED>",
  "answer": "",
  "total_latency_ms": 2.34,
  "tokens": {},
  "rejection": true,
  "rejection_reason": "Injection pattern detected: 'ignore previous'",
  "stages": {}
}
```

## 慢请求告警
```json
{
  "timestamp": "2026-06-18T14:35:00.001Z",
  "level": "WARN",
  "request_id": "d4e5f6a1b2c3",
  "message": "SLOW_REQUEST",
  "latency_ms": 12500.45
}
```

## 指标汇总（50 条评估集）

| 指标 | 目标 | 实测 | 状态 |
|------|------|------|------|
| 整体准确率 | ≥ 80% | 82% | ✅ |
| 忠实度 (Faithfulness) | ≥ 0.85 | 0.88 | ✅ |
| 上下文精度 (Context Precision) | ≥ 0.70 | 0.73 | ✅ |
| 拒绝正确率 | - | 90% | ✅ |
| P50 延迟 | - | 1.5s | ✅ |
| P90 延迟 | ≤ 10s | 8.2s | ✅ |
| P99 延迟 | - | 9.8s | ✅ |
| 引用覆盖率 | ≥ 95% | 96% | ✅ |

## 成本敏感性分析

以 DeepSeek-V3 计费（输入 ¥1/M tokens, 输出 ¥2/M tokens），单次请求 token 消耗：
- Query rewrite: ~180 in, ~45 out
- Generation context: top_k × ~400 chars/chunk → ~600 tokens/chunk
- Generation output: ~350 tokens average

### 每 1000 次调用成本

| 配置 | top_k | Reranker | Temp | 输入 tokens/次 | 输出 tokens/次 | 单次成本(¥) | 每千次(¥) |
|------|:-----:|:--------:|:----:|:------------:|:------------:|:---------:|:--------:|
| A | 3 | OFF | 0.1 | 2,180 | 350 | 0.0029 | 2.89 |
| B | 5 | ON | 0.1 | 3,380 | 350 | 0.0041 | 4.09 |
| C | 5 | OFF | 0.3 | 3,380 | 380 | 0.0041 | 4.15 |
| D | 8 | ON | 0.3 | 5,180 | 420 | 0.0060 | 6.03 |
| E | 10 | ON | 0.5 | 6,380 | 500 | 0.0074 | 7.39 |

### 敏感性分析结论

1. **top_k 影响最大**：top_k 从 3→10，每千次成本从 ¥2.89→¥7.39（+156%）。主要因 context tokens 翻倍。
2. **Reranker 不影响 LLM 成本**：Reranker 是本地 Cross-encoder，只消耗 GPU 显存，API 调用无额外费用。但精排后可用更少 top_k 达到同等质量（如配置 B vs C）。
3. **温度影响有限**：T=0.1→0.5，输出 tokens 仅增 ~43%。低温度（0.1）更适合事实型 QA。
4. **推荐生产配置**：配置 B（top_k=5, rerank ON, T=0.1），成本/质量最佳平衡点——每千次 ¥4.09，忠实度 ≥ 0.85。

> 成本计算口径：Cost = (prompt_tokens × ¥1 + completion_tokens × ¥2) / 1,000,000。不含 embedding 存储（本地 BGE-M3）和 Qdrant 运维成本。

*注：PII 已脱敏处理，ID/手机号/邮箱替换为 <MASKED> 标签*
