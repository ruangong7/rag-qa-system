# RAG QA System

基于内部知识库的检索增强生成（RAG）问答系统，支持多轮对话、引用回溯、双语文档（CN/EN）、结构化日志。

## Quick Start

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
# 编辑 .env：填入 LLM_API_KEY

# 3. 启动 Qdrant (Docker)
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# 4. 构建索引
python -c "from src.ingestion.indexer import build_index; build_index('./data/documents')"

# 5. 启动服务
python main.py
# → http://localhost:8000/docs (Swagger UI)
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | 发送问题，获取引用支持的回答 |
| POST | `/index` | 重建文档索引 |
| GET | `/health` | 健康检查 |

### POST /chat

Request:
```json
{
  "question": "员工手册中关于年假的规定是什么？",
  "session_id": null
}
```

Response:
```json
{
  "answer": "根据员工手册第3.2节，员工每年享有...",
  "citations": [
    {
      "index": 1,
      "source_file": "handbook_v3.pdf",
      "page_number": 12,
      "snippet": "3.2 年假制度\n员工每年享有..."
    }
  ],
  "session_id": "abc12345",
  "confidence": 0.88,
  "latency_ms": 1520.5
}
```

## Evaluation

```bash
# Run unit tests
pytest tests/ -v

# Run evaluation
python eval/evaluate.py http://localhost:8000
```

## Project Structure

```
rag-qa-system/
├── main.py                 # FastAPI entry
├── config.yaml             # All tunable parameters
├── src/
│   ├── ingestion/          # Document loading + OCR + chunking + indexing
│   ├── retrieval/          # Dense + Sparse + RRF Fusion + Rerank
│   ├── generation/         # LLM call + post-processing
│   ├── conversation/       # Session management
│   ├── safety/             # Prompt injection + PII masking
│   └── observability/      # Structured JSON logging
├── tests/                  # Unit tests
├── eval/                   # Evaluation set + script
└── docs/                   # Design notes
```
