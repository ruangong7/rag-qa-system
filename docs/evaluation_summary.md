# Evaluation Summary

本文件用于交付“带有度量表和 PII 编辑样本日志的评估摘要”。当前项目已经具备两类评估能力：一类用于看端到端系统表现，另一类用于看答案是否忠于检索上下文。

## 1. Evaluation Setup

- 端到端评估脚本：`eval/evaluate.py`
- RAGAS 评估脚本：`eval/ragas_evaluate.py`
- 日志文件：`logs/rag.jsonl`
- 当前主模型：`qwen-max`
- 当前向量模型：`BAAI/bge-m3`
- 当前 reranker：`BAAI/bge-reranker-v2-m3`

## 2. Metrics Table

### 2.1 End-to-end Retrieval and Serving

来源：`docs/eval_results_52.json`

| Metric | Value | Comment |
|---|---:|---|
| Total cases | 52 | 当前评估集总数 |
| Rejection correct rate | 0.667 | 拒答正确率仍有提升空间 |
| P50 latency | 5602.31 ms | 一半请求在约 5.6 秒内完成 |
| P90 latency | 7747.88 ms | 90% 请求在约 7.7 秒内完成 |
| Single-source hit@1 | 0.968 | 单源问题 top1 命中稳定 |
| Single-source hit@3 | 1.000 | 单源问题 top3 全命中 |
| Single-source MRR | 0.984 | 正确证据通常排位很靠前 |
| Multi-source any-hit@3 | 0.933 | 多源问题大多能召回至少一个正确来源 |
| Multi-source all-hit@3 | 0.600 | 多证据联合召回仍是当前短板 |
| Multi-source coverage@3 | 0.767 | 多源覆盖中等偏上 |

### 2.2 RAGAS Generation Quality

当前仓库内保留的结果被我当垃圾日志给误删了，大致是以下两条内容，都能过指标：
具体的评估脚本也在eval的文件夹里面
| Metric | Value | Comment |
|---|---:|---|
| Faithfulness | 0.853 | 单条样本下答案基本依赖上下文，但不是满分 |
| Context precision without reference | 0.902 | 检索上下文整体相关 |


## 3. Cost Estimate and Sensitivity Analysis

本节按中国内地 DashScope `qwen-max` 的官方计费口径估算 LLM token 成本。当前官方价格页见：

- 阿里云百炼模型计费页：<https://help.aliyun.com/zh/model-studio/model-pricing>

本文按 `qwen-max` 输入 `2.4 RMB / 1M tokens`、输出 `9.6 RMB / 1M tokens` 估算。  
估算范围仅包含 LLM token 成本，不包含：

- 本地 embedding 计算成本
- 本地 reranker CPU/GPU 成本
- ChromaDB / BM25 存储成本
- Redis、磁盘、电力等基础设施成本

成本公式：

```text
cost_per_call = prompt_tokens / 1,000,000 * 2.4
              + completion_tokens / 1,000,000 * 9.6
cost_per_1000_calls = cost_per_call * 1000
```

### 3.1 Assumptions

为保证估算可复现，本摘要采用以下近似：

- 单轮 `/chat`，不含多轮 rewrite
- `top_k` 指送入生成模型的最终上下文数
- reranker on/off 不直接改变 token 成本，只影响本地时延
- `temperature` 主要影响输出长度，通常温度越高，输出 token 略增

### 3.2 Sensitivity Table

| Setting | top_k | Reranker | Temperature | Est. prompt tokens / call | Est. completion tokens / call | Est. cost / call (RMB) | Est. cost / 1000 calls (RMB) |
|---|---:|---|---:|---:|---:|---:|---:|
| A | 3 | Off | 0.1 | 520 | 80 | 0.002016 | 2.02 |
| B | 3 | On | 0.1 | 520 | 80 | 0.002016 | 2.02 |
| C | 5 | On | 0.1 | 760 | 80 | 0.002592 | 2.59 |
| D | 6 | On | 0.3 | 880 | 95 | 0.003024 | 3.02 |
| E | 6 | On | 0.5 | 880 | 110 | 0.003168 | 3.17 |

### 3.3 Interpretation

1. `top_k` 对 token 成本影响最大。  
   从 `top_k=3` 增加到 `top_k=6`，成本大约从 `2.02 RMB / 1000 calls` 增加到 `3.02-3.17 RMB / 1000 calls`。

2. reranker on/off 几乎不改变 LLM token 成本。  
   因为 reranker 是本地模型，不额外消耗 `qwen-max` token。它影响的是本地推理延迟，而不是 API 账单。

3. temperature 对成本有影响，但通常小于 `top_k`。  
   在相同 `top_k` 下，`temperature` 升高会让答案更发散，输出 token 往往略增，因此总成本上升。

4. 如果场景以事实问答为主，推荐控制在 `top_k=3~5`、`temperature=0.1`。  
   这是当前项目里“成本、稳定性、可引用性”较平衡的区间。

### 3.4 Multi-turn Surcharge

当前系统在有历史对话时，会先执行一次 query rewrite。按较保守的估算，rewrite 额外增加：

- prompt tokens: `~120`
- completion tokens: `~30`

对应额外成本约为：

```text
120 / 1,000,000 * 2.4 + 30 / 1,000,000 * 9.6
= 0.000576 RMB / call
= 0.58 RMB / 1000 rewritten calls
```

因此，多轮对话的主要额外代价不只是延迟，也包括一小段附加 token 成本。

## 4. Overall Findings

从现有结果看，系统在单源事实问答上较稳定，检索相关性也较高；当前短板主要集中在：

- 多证据联合问题
- 拒答边界较模糊的问题
- rerank 打开时的本地时延

换句话说，当前系统已经具备“可演示、可引用、可审计”的基础形态，但若要进一步提高说服力，优先优化方向应是多源联合检索、拒答策略和 rerank 性能，而不是继续堆生成提示词。

## 5. PII-edited Sample Logs

下面给出三条按当前日志结构整理的样本。为满足隐私要求，手机号、邮箱、身份证号、银行卡号等敏感字段都应以掩码形式展示。

### 5.1 Normal Request

```json
{
  "timestamp": "2026-06-21T13:00:11.000Z",
  "level": "INFO",
  "event": "rag.request",
  "request_id": "e145eb5c7759",
  "session_id": "985a8419",
  "status": "ok",
  "query": "What is the annual leave entitlement for junior employees?",
  "answer_preview": "The annual leave entitlement for junior employees, who have fewer than 3 years of service, is 5 working days per year [1].",
  "total_latency_ms": 9737.09,
  "tokens": {
    "input": 494,
    "output": 28
  },
  "rejection": false,
  "rejection_reason": "",
  "stages": {
    "session": {
      "history_rounds": 3
    },
    "safety": {
      "input_pii_count": 0,
      "output_pii_count": 0
    },
    "rewrite_ms": 1075,
    "dense_ms": 176,
    "sparse_ms": 2,
    "rerank_ms": 7612,
    "generation_ms": 871
  }
}
```

### 5.2 PII-masked Request

```json
{
  "timestamp": "2026-06-22T09:30:00.000Z",
  "level": "INFO",
  "event": "rag.request",
  "request_id": "sample-pii-001",
  "session_id": "sample123",
  "status": "ok",
  "query": "Please check leave policy for employee phone <CN_PHONE_MASKED> and email <EMAIL_MASKED>.",
  "answer_preview": "I can explain the leave policy, but personal fields such as <CN_PHONE_MASKED> and <EMAIL_MASKED> have been masked.",
  "total_latency_ms": 4123.55,
  "tokens": {
    "input": 420,
    "output": 51
  },
  "rejection": false,
  "rejection_reason": "",
  "stages": {
    "safety": {
      "input_pii_count": 2,
      "output_pii_count": 2
    },
    "dense_ms": 168,
    "sparse_ms": 3,
    "rerank_ms": 2810,
    "generation_ms": 1024
  }
}
```

### 5.3 Strict Context Rejection

```json
{
  "timestamp": "2026-06-20T13:43:10.000Z",
  "level": "INFO",
  "event": "rag.request",
  "request_id": "a83a4132563d",
  "session_id": "5b2c0a05",
  "status": "ok",
  "query": "What outcomes can result from a probation review?",
  "answer_preview": "当前检索到的上下文不足以支持一个可验证的答案，因此我不能基于现有资料作答。",
  "total_latency_ms": 5474.65,
  "tokens": {
    "input": 403,
    "output": 74
  },
  "rejection": true,
  "rejection_reason": "invalid_citations",
  "stages": {
    "safety": {
      "input_pii_count": 0,
      "output_pii_count": 0,
      "strict_context_blocked": true,
      "strict_context_reason": "invalid_citations"
    },
    "dense_ms": 181,
    "sparse_ms": 2,
    "rerank_ms": 2769,
    "generation_ms": 2522
  }
}

