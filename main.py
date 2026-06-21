"""RAG QA System FastAPI application."""
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.conversation.session import SessionManager
from src.generation.llm import generate_answer, get_llm_client, rewrite_query
from src.generation.postprocess import mask_pii, validate_citations
from src.ingestion.indexer import get_collection
from src.observability.logger import RAGLogger
from src.observability.trace import build_traceparent, parse_or_create_trace
from src.retrieval import retrieve
from src.retrieval.sparse import build_bm25_index, load_bm25_index, save_bm25_index
from src.safety import REJECTION_TEMPLATES, check_injection, mask_pii as mask_pii_input

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _llm_model() -> str:
    return os.getenv("LLM_MODEL", "qwen-max")


def _build_session_manager():
    max_history = int(os.getenv("MAX_HISTORY_ROUNDS", "5"))
    ttl_seconds = int(os.getenv("SESSION_TTL", "3600"))
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            from src.conversation.redis_session import RedisSessionManager

            manager = RedisSessionManager(redis_url, max_history=max_history, ttl_seconds=ttl_seconds)
            manager.ping()
            return manager
        except Exception:
            pass
    return SessionManager(max_history=max_history, ttl_seconds=ttl_seconds)


session_mgr = _build_session_manager()
rag_logger = RAGLogger()
chroma_collection = None
llm_client = None


def _summarize_contexts(documents: list[dict]) -> list[dict]:
    summary = []
    for rank, doc in enumerate(documents, start=1):
        summary.append(
            {
                "rank": rank,
                "source_file": doc.get("source_file", "unknown"),
                "page_number": doc.get("page_number", 1),
                "section": doc.get("section", ""),
                "section_path": doc.get("section_path", ""),
                "doc_title": doc.get("doc_title", ""),
                "score": doc.get("score"),
                "rrf_score": doc.get("rrf_score"),
                "rerank_score": doc.get("rerank_score"),
                "snippet_preview": mask_pii(doc.get("text", "")[:180]),
            }
        )
    return summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    global chroma_collection, llm_client

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
    bm25_path = os.getenv("BM25_INDEX_PATH", os.path.join(persist_dir, "bm25.pkl"))

    try:
        chroma_collection = get_collection(persist_dir)
        count = chroma_collection.count()
        if count > 0 and not load_bm25_index(bm25_path):
            from chromadb import PersistentClient
            from chromadb.config import Settings

            client = PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
            col = client.get_collection(os.getenv("CHROMA_COLLECTION", "rag_docs"))
            results = col.get(include=["documents", "metadatas"])
            chunks = []
            for i in range(len(results["ids"])):
                chunks.append({"text": results["documents"][i], "metadata": results["metadatas"][i]})
            build_bm25_index(chunks)
            save_bm25_index(bm25_path)
    except Exception:
        pass

    llm_client = get_llm_client(
        api_key=os.getenv("DASHSCOPE_API_KEY") or os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    )
    yield


app = FastAPI(title="RAG QA System", version="0.2.0", lifespan=lifespan)

STATIC_DIR = Path(__file__).with_name("static")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    question: str = Field(..., max_length=2000)
    session_id: Optional[str] = None


class Citation(BaseModel):
    index: int
    source_file: str
    page_number: int
    snippet: str = Field(max_length=200)


class RetrievedContext(BaseModel):
    index: int
    source_file: str
    page_number: int
    snippet: str = Field(max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_contexts: list[RetrievedContext] = []
    session_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float


class IndexRequest(BaseModel):
    data_dir: str = "./data/documents"


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request, response: Response):
    t_start = time.time()
    request_id = uuid.uuid4().hex[:12]
    trace_ctx = parse_or_create_trace(dict(request.headers))
    traceparent = build_traceparent(trace_ctx)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = trace_ctx["trace_id"]
    response.headers["traceparent"] = traceparent
    stages = {"trace": trace_ctx.copy()}

    session_id = req.session_id or session_mgr.create_session()
    history = session_mgr.get_history(session_id, rounds=3)
    stages["session"] = {"history_rounds": len(history) // 2}

    masked_query, input_pii_count = mask_pii_input(req.question)
    stages["safety"] = {"input_pii_count": input_pii_count}
    is_safe, reason = check_injection(req.question)
    if not is_safe:
        total_ms = round((time.time() - t_start) * 1000, 2)
        rag_logger.log_request(
            request_id=request_id,
            session_id=session_id,
            query=masked_query,
            stages=stages,
            total_latency_ms=total_ms,
            rejection=True,
            rejection_reason=reason,
            trace_id=trace_ctx["trace_id"],
            span_id=trace_ctx["span_id"],
            traceparent=traceparent,
        )
        return ChatResponse(
            answer=REJECTION_TEMPLATES["injection"],
            citations=[],
            retrieved_contexts=[],
            session_id=session_id,
            confidence=0.0,
            latency_ms=total_ms,
        )

    t0 = time.time()
    if history:
        rewritten = rewrite_query(llm_client, _llm_model(), history, req.question)
    else:
        rewritten = req.question
    stages["rewrite_ms"] = round((time.time() - t0) * 1000)
    masked_rewritten, rewritten_pii_count = mask_pii_input(rewritten)
    stages["query"] = {"rewritten": masked_rewritten, "rewrite_pii_count": rewritten_pii_count}

    documents, retrieval_timing = retrieve(
        query=rewritten,
        collection=chroma_collection,
        dense_top_k=int(os.getenv("RETRIEVAL_DENSE_TOP_K", "20")),
        sparse_top_k=int(os.getenv("RETRIEVAL_SPARSE_TOP_K", "20")),
        fusion_top_k=int(os.getenv("RETRIEVAL_FUSION_TOP_K", "10")),
        rerank_top_k=int(os.getenv("RETRIEVAL_FINAL_TOP_K", "3")),
        enable_rerank=_env_bool("RETRIEVAL_ENABLE_RERANK", True),
    )
    stages.update(retrieval_timing)
    stages["retrieval_config"] = {
        "dense_top_k": int(os.getenv("RETRIEVAL_DENSE_TOP_K", "20")),
        "sparse_top_k": int(os.getenv("RETRIEVAL_SPARSE_TOP_K", "20")),
        "fusion_top_k": int(os.getenv("RETRIEVAL_FUSION_TOP_K", "10")),
        "final_top_k": int(os.getenv("RETRIEVAL_FINAL_TOP_K", "3")),
        "rerank_enabled": _env_bool("RETRIEVAL_ENABLE_RERANK", True),
        "reranker_model": os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
    }
    stages["retrieved_contexts"] = _summarize_contexts(documents)

    if not documents:
        total_ms = round((time.time() - t_start) * 1000, 2)
        rag_logger.log_request(
            request_id=request_id,
            session_id=session_id,
            query=masked_query,
            stages=stages,
            total_latency_ms=total_ms,
            rejection=True,
            rejection_reason="no_results",
            trace_id=trace_ctx["trace_id"],
            span_id=trace_ctx["span_id"],
            traceparent=traceparent,
        )
        return ChatResponse(
            answer=REJECTION_TEMPLATES["no_results"],
            citations=[],
            retrieved_contexts=[],
            session_id=session_id,
            confidence=0.0,
            latency_ms=total_ms,
        )

    low_conf_score = float(stages.get("dense_top_similarity", 0.0))
    low_conf_threshold = float(os.getenv("RETRIEVAL_LOW_CONFIDENCE_THRESHOLD", "0.35"))
    if low_conf_score and low_conf_score < low_conf_threshold:
        total_ms = round((time.time() - t_start) * 1000, 2)
        rag_logger.log_request(
            request_id=request_id,
            session_id=session_id,
            query=masked_query,
            stages=stages,
            total_latency_ms=total_ms,
            rejection=True,
            rejection_reason="low_confidence",
            trace_id=trace_ctx["trace_id"],
            span_id=trace_ctx["span_id"],
            traceparent=traceparent,
        )
        return ChatResponse(
            answer=REJECTION_TEMPLATES["low_confidence"],
            citations=[],
            retrieved_contexts=[],
            session_id=session_id,
            confidence=round(low_conf_score, 2),
            latency_ms=total_ms,
        )

    t0 = time.time()
    gen_result = generate_answer(
        client=llm_client,
        model=_llm_model(),
        system_prompt=(
            "You are an internal knowledge-base QA assistant. Answer strictly from the retrieved context; do not invent facts. "
            "If the context contains relevant facts, answer directly and do not claim the question is incomplete. "
            "Only say the knowledge base does not contain the information when none of the retrieved contexts supports the answer. "
            "Every factual statement must cite context numbers such as [1] or [2]. "
            "Answer in the user's main language. Preserve exact proper nouns, acronyms, system names, and factual values from the context."
        ),
        user_query=req.question,
        contexts=documents,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
    )
    stages["generation_ms"] = round((time.time() - t0) * 1000)
    answer = gen_result["answer"]
    tokens = {"input": gen_result["input_tokens"], "output": gen_result["output_tokens"]}

    t0 = time.time()
    cit_result = validate_citations(answer, len(documents))
    masked_answer = mask_pii(answer)
    output_pii_count = masked_answer.count("_MASKED>")
    answer = masked_answer
    stages["citation_validation"] = cit_result
    stages["safety"]["output_pii_count"] = output_pii_count
    stages["postprocess_ms"] = round((time.time() - t0) * 1000)

    retrieved_contexts = []
    for i, doc in enumerate(documents, start=1):
        retrieved_contexts.append(
            RetrievedContext(
                index=i,
                source_file=doc.get("source_file", "unknown"),
                page_number=doc.get("page_number", 1),
                snippet=doc.get("text", "")[:4000],
            )
        )

    citations = []
    cited_indices = set(cit_result.get("citations_valid", []))
    docs_for_citations = [(i, doc) for i, doc in enumerate(documents, start=1) if not cited_indices or i in cited_indices]
    for i, doc in docs_for_citations:
        citations.append(
            Citation(
                index=i,
                source_file=doc.get("source_file", "unknown"),
                page_number=doc.get("page_number", 1),
                snippet=doc.get("text", "")[:200],
            )
        )

    citation_coverage = cit_result["citations_found"] / max(cit_result["citations_total"], 1)
    top_similarity = float(stages.get("top_similarity") or stages.get("dense_top_similarity") or 0.0)
    confidence = round((citation_coverage + min(top_similarity, 1.0)) / 2, 2)
    if not cit_result["valid"]:
        confidence = min(confidence, 0.35)

    unsupported_reason = "invalid_citations" if not cit_result["valid"] else ""
    if _env_bool("STRICT_CONTEXT_ENFORCEMENT", True) and unsupported_reason:
        stages["safety"]["strict_context_blocked"] = True
        stages["safety"]["strict_context_reason"] = unsupported_reason
        total_ms = round((time.time() - t_start) * 1000, 2)
        rag_logger.log_request(
            request_id=request_id,
            session_id=session_id,
            query=masked_query,
            stages=stages,
            answer=REJECTION_TEMPLATES["unsupported_answer"],
            total_latency_ms=total_ms,
            tokens=tokens,
            rejection=True,
            rejection_reason=unsupported_reason,
            trace_id=trace_ctx["trace_id"],
            span_id=trace_ctx["span_id"],
            traceparent=traceparent,
        )
        return ChatResponse(
            answer=REJECTION_TEMPLATES["unsupported_answer"],
            citations=[],
            retrieved_contexts=retrieved_contexts,
            session_id=session_id,
            confidence=min(confidence, 0.3),
            latency_ms=total_ms,
        )

    total_ms = round((time.time() - t_start) * 1000, 2)
    rag_logger.log_request(
        request_id=request_id,
        session_id=session_id,
        query=masked_query,
        stages=stages,
        answer=answer,
        total_latency_ms=total_ms,
        tokens=tokens,
        trace_id=trace_ctx["trace_id"],
        span_id=trace_ctx["span_id"],
        traceparent=traceparent,
    )
    if total_ms > float(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "10000")):
        rag_logger.log_alert(
            request_id,
            "SLOW_REQUEST",
            latency_ms=total_ms,
            trace_id=trace_ctx["trace_id"],
            span_id=trace_ctx["span_id"],
            traceparent=traceparent,
        )

    session_mgr.add_turn(session_id, req.question, answer)
    return ChatResponse(
        answer=answer,
        citations=citations,
        retrieved_contexts=retrieved_contexts,
        session_id=session_id,
        confidence=confidence,
        latency_ms=total_ms,
    )


@app.get("/", include_in_schema=False)
async def frontend():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend assets not found")
    return FileResponse(index_file)


@app.post("/index")
async def index_documents(req: IndexRequest):
    from src.ingestion.indexer import build_index

    try:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        count = build_index(data_dir=req.data_dir, persist_dir=persist_dir)
        return {"status": "ok", "documents_indexed": count}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
        reload=_env_bool("RELOAD", False),
    )
