"""
RAG QA System - FastAPI Application
ChromaDB 版本 — 纯 Python, 无需 Docker, CPU 可运行
"""
import time
import uuid
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.ingestion.indexer import get_collection
from src.retrieval.sparse import build_bm25_index
from src.retrieval import retrieve
from src.generation.llm import get_llm_client, generate_answer, rewrite_query
from src.generation.postprocess import validate_citations, check_answer_faithfulness, mask_pii
from src.conversation.session import SessionManager
from src.safety import check_injection, mask_pii as mask_pii_input, REJECTION_TEMPLATES
from src.observability.logger import RAGLogger

from dotenv import load_dotenv
load_dotenv()

# ─── Globals ───────────────────────────────────────────
session_mgr = SessionManager(
    max_history=int(os.getenv("MAX_HISTORY_ROUNDS", "5")),
    ttl_seconds=int(os.getenv("SESSION_TTL", "3600")),
)
rag_logger = RAGLogger()

chroma_collection = None
llm_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chroma_collection, llm_client

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
    try:
        chroma_collection = get_collection(persist_dir)
        # 如果是新 collection（空），尝试重建 BM25
        count = chroma_collection.count()
        if count > 0:
            from chromadb import PersistentClient
            from chromadb.config import Settings
            client = PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
            col = client.get_collection("rag_docs")
            results = col.get(include=["documents", "metadatas"])
            chunks = []
            for i in range(len(results["ids"])):
                chunks.append({
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i],
                })
            build_bm25_index(chunks)
    except Exception:
        pass  # collection 不存在, 先调用 /index

    llm_client = get_llm_client(
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL"),
    )
    yield


app = FastAPI(
    title="RAG QA System",
    version="0.2.0",
    lifespan=lifespan,
)

# ─── Models ────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., max_length=2000)
    session_id: Optional[str] = None

class Citation(BaseModel):
    index: int
    source_file: str
    page_number: int
    snippet: str = Field(max_length=200)

class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    session_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float

class IndexRequest(BaseModel):
    data_dir: str = "./data/documents"


# ─── Routes ────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    t_start = time.time()
    request_id = uuid.uuid4().hex[:12]
    stages = {}

    # 1. Session
    session_id = req.session_id or session_mgr.create_session()
    history = session_mgr.get_history(session_id, rounds=3)
    stages["session"] = {"history_rounds": len(history) // 2}

    # 2. Safety check
    is_safe, reason = check_injection(req.question)
    if not is_safe:
        rag_logger.log_request(request_id, session_id, req.question,
                               stages, rejection=True, rejection_reason=reason)
        return ChatResponse(
            answer=REJECTION_TEMPLATES["injection"],
            citations=[],
            session_id=session_id,
            confidence=0.0,
            latency_ms=round((time.time() - t_start) * 1000, 2),
        )

    # 3. Query rewrite
    t0 = time.time()
    if history:
        rewritten = rewrite_query(llm_client, os.getenv("LLM_MODEL", "deepseek-chat"), history, req.question)
    else:
        rewritten = req.question
    stages["rewrite_ms"] = round((time.time() - t0) * 1000)

    # 4. Retrieval
    documents, retrieval_timing = retrieve(
        query=rewritten,
        collection=chroma_collection,
    )
    stages.update(retrieval_timing)

    # 5. Rejection
    if not documents:
        rag_logger.log_request(request_id, session_id, req.question,
                               stages, rejection=True, rejection_reason="no_results")
        return ChatResponse(
            answer=REJECTION_TEMPLATES["no_results"],
            citations=[],
            session_id=session_id,
            confidence=0.0,
            latency_ms=round((time.time() - t_start) * 1000, 2),
        )

    # 6. Generation
    t0 = time.time()
    gen_result = generate_answer(
        client=llm_client,
        model=os.getenv("LLM_MODEL", "deepseek-chat"),
        system_prompt=(
            "你是内部知识库助手。严格基于以下检索内容回答，不得编造。"
            "如果检索内容不足以回答问题，明确说明'当前知识库不包含该信息'。"
            "每条陈述必须标注来源 [文件 § 段落号]。回答语言与用户问题一致。"
        ),
        user_query=req.question,
        contexts=documents,
        temperature=0.1,
        max_tokens=1024,
    )
    stages["generation_ms"] = round((time.time() - t0) * 1000)
    answer = gen_result["answer"]
    tokens = {"input": gen_result["input_tokens"], "output": gen_result["output_tokens"]}

    # 7. Post-process
    t0 = time.time()
    cit_result = validate_citations(answer, len(documents))
    faith_score = check_answer_faithfulness(answer, documents)
    answer = mask_pii(answer)
    stages["postprocess_ms"] = round((time.time() - t0) * 1000)

    # 8. Citations
    citations = []
    for i, doc in enumerate(documents, start=1):
        citations.append(Citation(
            index=i,
            source_file=doc.get("source_file", "unknown"),
            page_number=doc.get("page_number", 1),
            snippet=doc.get("text", "")[:200],
        ))

    citation_coverage = cit_result["citations_found"] / max(cit_result["citations_total"], 1)
    confidence = round((faith_score + citation_coverage) / 2, 2)

    # 9. Log
    total_ms = round((time.time() - t_start) * 1000, 2)
    rag_logger.log_request(
        request_id=request_id,
        session_id=session_id,
        query=mask_pii_input(req.question)[0],
        stages=stages,
        answer=answer,
        total_latency_ms=total_ms,
        tokens=tokens,
    )
    if total_ms > 10000:
        rag_logger.log_alert(request_id, "SLOW_REQUEST", latency_ms=total_ms)

    # 10. Update session
    session_mgr.add_turn(session_id, req.question, answer)

    return ChatResponse(
        answer=answer,
        citations=citations,
        session_id=session_id,
        confidence=confidence,
        latency_ms=total_ms,
    )


@app.post("/index")
async def index_documents(req: IndexRequest):
    """Build/rebuilt search index"""
    from src.ingestion.indexer import build_index
    from src.ingestion.loader import load_all_documents
    from pathlib import Path
    try:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        count = build_index(
            data_dir=req.data_dir,
            persist_dir=persist_dir,
        )
        # 同步构建 BM25 索引
        chunks = load_all_documents(Path(req.data_dir))
        build_bm25_index(chunks)
        return {"status": "ok", "documents_indexed": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "vector_db": "ChromaDB (local, CPU)",
        "documents_indexed": chroma_collection.count() if chroma_collection else 0,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
