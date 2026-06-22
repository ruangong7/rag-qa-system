# RAG QA System

本项目是一个本地可运行的 RAG 问答 Demo，面向“内部知识库问答”场景。系统使用 FastAPI 提供接口和简易对话前端，使用本地 ChromaDB 保存向量索引，结合 BM25 稀疏检索、BGE-M3 向量检索、RRF 融合和可选 rerank，对知识库进行中英文检索，并通过 Qwen-Max 生成带引用的答案。

当前版本重点覆盖这些能力：

- 本地索引构建，启动后直接查，不会每次重新切分文档
- `/chat`、`/index`、`/health` 三个主要接口
- 同一会话内的多轮对话连续性
- 引用校验和低置信拒答
- 基本 prompt injection 防护与 PII 脱敏
- 结构化日志，便于排查延迟、检索和生成问题
- 自定义评估脚本 + RAGAS 评估脚本

## Architecture

- LLM: DashScope OpenAI-compatible API，默认 `qwen-max`
- Dense retrieval: `BAAI/bge-m3`
- Sparse retrieval: `rank-bm25`
- Fusion: RRF
- Reranker: `BAAI/bge-reranker-v2-m3`，可开关
- Vector store: 本地 `ChromaDB`
- Session memory:
  - 默认内存版 `SessionManager`
  - 配置 `REDIS_URL` 后自动切 Redis

## Project Structure

```text
rag-qa-system/
├─ main.py
├─ requirements.txt
├─ .env.example
├─ config.yaml
├─ data/
│  └─ documents/
├─ chroma_data/
├─ eval/
│  ├─ eval_set.json
│  ├─ evaluate.py
│  └─ ragas_evaluate.py
├─ logs/
├─ scripts/
│  ├─ build_index.py
│  └─ latency_probe.py
├─ src/
│  ├─ conversation/
│  ├─ generation/
│  ├─ ingestion/
│  ├─ observability/
│  ├─ retrieval/
│  └─ safety/
└─ static/
```

## Requirements

- Python 3.11+
- Windows / Linux / macOS 均可，本仓库当前主要按 Windows 本地环境验证
- DashScope API Key
- 首次跑 embedding / reranker 时，需要本地已有 Hugging Face 模型，或能联网下载

建议先创建并激活虚拟环境，再安装依赖：

```powershell
cd F:\aia\rag-qa-system
pip install -r requirements.txt
```

如果你准备离线运行，请先把 `bge-m3` 和 `bge-reranker-v2-m3` 下载到本地缓存，再打开：

```env
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

## Environment

先复制配置文件：

```powershell
Copy-Item .env.example .env
```

至少需要确认这些变量：

```env
LLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=your-real-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max

CHROMA_PERSIST_DIR=./chroma_data
BM25_INDEX_PATH=./chroma_data/bm25.pkl

EMBEDDING_MODEL=BAAI/bge-m3
RETRIEVAL_ENABLE_RERANK=false
WARMUP_DENSE_ON_STARTUP=true
```

如果本地 reranker 已下载，建议把 `RERANKER_MODEL` 指到本地 snapshot 路径，避免每次访问 Hugging Face。

如果要启用 Redis 会话存储：

```env
REDIS_URL=redis://localhost:6379/0
```

## Data and Indexing

知识库源文件默认放在 `data/documents/`。

当前重建版 loader 主要稳定支持：

- `.md`
- `.txt`

`loader.py` 采用“结构化 markdown 分块”：

- 按标题层级解析 section
- 每个 chunk 保留 `doc_title`、`section`、`section_path`
- chunk 文本前面会带上文档名、章节路径、部门等头信息
- section 过长时再按字符长度切小块，默认 `chunk_size=1200`，`overlap=150`

构建索引命令：

```powershell
python scripts/build_index.py
```

也可以手动指定目录：

```powershell
python scripts/build_index.py --data-dir data/documents --persist-dir chroma_data
```

构建完成后：

- 向量索引持久化在 `chroma_data/`
- BM25 索引持久化在 `chroma_data/bm25.pkl`
- 后续启动服务会直接加载索引，不会重新切分全部文档

## Run the Service

启动服务：

```powershell
python main.py
```

启动后可访问：

- 前端聊天页: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`
- 健康检查: `http://127.0.0.1:8000/health`

如果端口 8000 被占用，可以先清理占用进程，或改 `.env` 中的 `PORT`。

## API

### `POST /chat`

请求：

```json
{
  "question": "员工手册中关于年假的规定是什么？",
  "session_id": null
}
```

返回：

```json
{
  "answer": "初级员工每年 5 个工作日，中级员工每年 10 个工作日，高级员工每年 15 个工作日。[1]",
  "citations": [
    {
      "index": 1,
      "source_file": "employee_handbook.md",
      "page_number": 1,
      "snippet": "### 3.1 Annual Leave ..."
    }
  ],
  "retrieved_contexts": [
    {
      "index": 1,
      "source_file": "employee_handbook.md",
      "page_number": 1,
      "snippet": "Document: Employee Handbook v3.2 ..."
    }
  ],
  "session_id": "985a8419",
  "confidence": 0.84,
  "latency_ms": 9737.09
}
```

说明：

- `citations` 是最终答案实际引用到的片段
- `retrieved_contexts` 是本轮送入生成模型的上下文
- `confidence` 由检索分数和引用覆盖度共同决定，并限制在 `[0, 1]`

### `POST /index`

用于重建索引：

```json
{
  "data_dir": "./data/documents"
}
```

### `GET /health`

返回服务状态和当前已加载的文档数。

## Multi-turn Memory

系统支持同一 `session_id` 下的多轮对话。

当前实现方式：

- 保存最近若干轮历史消息
- 新问题到来时，若存在历史，会先调用一次 LLM 做 query rewrite
- rewrite 后再进行检索和生成

默认行为：

- `MAX_HISTORY_ROUNDS=5`
- 实际 rewrite 使用最近 3 轮历史
- 默认短期记忆存在内存中
- 配置 `REDIS_URL` 后可切到 Redis

这意味着一次带上下文的问答，通常会调用两次大模型：

1. `rewrite_query`
2. `generate_answer`

无历史时通常只调用一次生成模型。

## Safety

当前安全策略包含三层：

1. 输入侧最小注入防护  
   `src/safety` 中使用规则拦截明显的 prompt injection 模式。

2. PII 脱敏  
   对输入和输出做基础正则脱敏，覆盖手机号、邮箱、身份证号等。

3. 严格依赖检索上下文  
   答案必须带有效引用；若引用校验失败，在 `STRICT_CONTEXT_ENFORCEMENT=true` 时直接拒答。

当前这套是“课程作业 / Demo 可交付”级别，不是生产级纵深防护。

## Logging and Observability

日志重点用于三类问题排查：

- 请求慢在哪一段
- 检索拿到了什么片段
- 大模型到底调了几次、用了多少 token

当前日志会记录：

- `rag.request`
- `llm.call`
- `SLOW_REQUEST`
- trace 信息：`trace_id`、`span_id`、`traceparent`

典型字段包括：

- `rewrite_ms`
- `dense_ms`
- `sparse_ms`
- `fusion_ms`
- `rerank_ms`
- `generation_ms`
- `retrieved_contexts`
- `tokens`
- `rejection`
- `rejection_reason`

日志目录：`logs/`

## Evaluation

### 1. 自定义端到端评估

主要看：

- retrieval accuracy
- citation accuracy
- overall accuracy
- rejection rate
- P50 / P90 latency

运行：

```powershell
python -m eval.evaluate http://127.0.0.1:8000
```

保存为 UTF-8 文件：

```powershell
python -m eval.evaluate http://127.0.0.1:8000 | Out-File -Encoding utf8 docs\eval_results_current.json
```

### 2. RAGAS 评估

主要看：

- `faithfulness`
- `context_precision_without_reference`

运行前需要配置 judge model：

```powershell
$env:RAGAS_LLM_API_KEY="your-key"
$env:RAGAS_LLM_BASE_URL="https://your-base-url/v1"
$env:RAGAS_LLM_MODEL="gpt-4o-mini"
```

然后执行：

```powershell
python -m eval.ragas_evaluate http://127.0.0.1:8000 --limit 10 --out docs\ragas_eval_10.json
```

全量运行：

```powershell
python -m eval.ragas_evaluate http://127.0.0.1:8000 --out docs\ragas_eval.json
```

说明：

- RAGAS 会比普通评估慢很多，因为它会额外调用 judge model
- 如果只是 smoke test，建议先跑 `--limit 1` 或 `--limit 10`

## Common Issues

### 1. 启动卡在 `Waiting for application startup`

通常是启动阶段正在做这些事：

- 加载 ChromaDB collection
- 必要时从 Chroma 重建 BM25
- 预热 embedding 模型

如果模型较大或本地磁盘慢，这里会停几秒到几十秒。

### 2. 每次启动都访问 Hugging Face

说明 embedding 或 reranker 没完全切到本地路径，或者离线标志没配好。请检查：

- `HF_HUB_OFFLINE=1`
- `TRANSFORMERS_OFFLINE=1`
- `RERANKER_MODEL` 是否是本地 snapshot 路径

### 3. 问题一发就 500

优先看：

- `logs/` 里的结构化日志
- 控制台 traceback
- `.env` 里的模型路径和开关

### 4. 评估输出乱码

PowerShell 的 `>` 有时会写成 UTF-16。建议统一使用：

```powershell
| Out-File -Encoding utf8
```

### 5. rerank 很慢

这是当前端到端延迟里最重的一段之一，尤其在 CPU 上会比较明显。需要速度优先时，可以先：

```env
RETRIEVAL_ENABLE_RERANK=false
```

## Test

```powershell
pytest tests -v
```

- 补全 PDF / OCR loader 的稳定支持
- 引入更稳的语义分块策略
- 优化 rerank 性能
- 强化拒答与 injection 防护
- 增加真实多轮评测集
