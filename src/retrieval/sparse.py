"""Sparse retrieval with BM25 persistence."""
import pickle
import re
from pathlib import Path
from typing import List

from rank_bm25 import BM25Okapi

_bm25_corpus = None
_bm25_texts = []
_bm25_metadata = []


def _tokenize(text: str) -> List[str]:
    tokens = []
    tokens.extend(w.lower() for w in re.findall(r"[a-zA-Z0-9]+", text))
    for seg in re.findall(r"[\u4e00-\u9fff]+", text):
        tokens.extend(list(seg))
    return tokens


def build_bm25_index(chunks: List[dict]):
    global _bm25_corpus, _bm25_texts, _bm25_metadata
    _bm25_texts = []
    _bm25_metadata = []
    tokenized = []

    for i, chunk in enumerate(chunks):
        tokenized.append(_tokenize(chunk["text"]))
        meta = chunk.get("metadata", {})
        _bm25_texts.append(chunk["text"])
        _bm25_metadata.append(
            {
                "id": str(i),
                "source_file": meta.get("source_file", ""),
                "page_number": meta.get("page_number", 1),
                "section": meta.get("section", ""),
                "section_path": meta.get("section_path", ""),
                "doc_title": meta.get("doc_title", ""),
                "department": meta.get("department", "General"),
            }
        )
    _bm25_corpus = BM25Okapi(tokenized)


def save_bm25_index(path: str):
    if _bm25_corpus is None:
        return False
    payload = {"texts": _bm25_texts, "metadata": _bm25_metadata}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        pickle.dump(payload, fh)
    return True


def load_bm25_index(path: str):
    global _bm25_corpus, _bm25_texts, _bm25_metadata
    file_path = Path(path)
    if not file_path.exists():
        return False
    with open(file_path, "rb") as fh:
        payload = pickle.load(fh)
    _bm25_texts = payload["texts"]
    _bm25_metadata = payload["metadata"]
    _bm25_corpus = BM25Okapi([_tokenize(t) for t in _bm25_texts])
    return True


def sparse_search(query: str, top_k: int = 20) -> List[dict]:
    if _bm25_corpus is None:
        return []

    scores = _bm25_corpus.get_scores(_tokenize(query))
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for idx, score in ranked:
        if score <= 0:
            continue
        meta = _bm25_metadata[idx]
        results.append(
            {
                "id": meta["id"],
                "text": _bm25_texts[idx],
                "score": round(float(score), 4),
                "source_file": meta["source_file"],
                "page_number": meta["page_number"],
                "section": meta.get("section", ""),
                "section_path": meta.get("section_path", ""),
                "doc_title": meta.get("doc_title", ""),
                "department": meta.get("department", "General"),
            }
        )
    return results
