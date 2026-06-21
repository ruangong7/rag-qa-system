import os
import time

from dotenv import load_dotenv


def log(label: str):
    print(label, flush=True)


def main():
    t0 = time.time()
    load_dotenv(".env")
    log(f"dotenv ok {time.time() - t0:.2f}s")

    t0 = time.time()
    from src.ingestion.indexer import get_collection

    log(f"import get_collection ok {time.time() - t0:.2f}s")

    t0 = time.time()
    from src.retrieval.sparse import load_bm25_index

    log(f"import sparse ok {time.time() - t0:.2f}s")

    t0 = time.time()
    from src.generation.llm import get_llm_client

    log(f"import llm ok {time.time() - t0:.2f}s")

    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
    bm25_path = os.getenv("BM25_INDEX_PATH", os.path.join(persist_dir, "bm25.pkl"))

    t0 = time.time()
    col = get_collection(persist_dir)
    log(f"get_collection ok {time.time() - t0:.2f}s")

    t0 = time.time()
    count = col.count()
    log(f"count={count} {time.time() - t0:.2f}s")

    t0 = time.time()
    loaded = load_bm25_index(bm25_path)
    log(f"bm25 loaded={loaded} {time.time() - t0:.2f}s")

    t0 = time.time()
    client = get_llm_client(
        api_key=os.getenv("DASHSCOPE_API_KEY") or os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
    )
    log(f"llm client={type(client).__name__} {time.time() - t0:.2f}s")


if __name__ == "__main__":
    main()
