"""Sparse retrieval - 内存 BM25 (rank-bm25 library)"""
import logging
from typing import List
from rank_bm25 import BM25Okapi
import re

logger = logging.getLogger(__name__)

# 全局: 文档语料 (建索引时填充)
_bm25_corpus = None
_bm25_texts = []
_bm25_metadata = []


def build_bm25_index(chunks: List[dict]):
    """从 chunk 列表构建 BM25 索引 (在 build_index 时调用)"""
    global _bm25_corpus, _bm25_texts, _bm25_metadata

    _bm25_texts = []
    _bm25_metadata = []
    tokenized = []

    for i, chunk in enumerate(chunks):
        text = chunk["text"]
        # 简单分词: 英文按空格, 中文按字符
        tokens = _tokenize(text)
        tokenized.append(tokens)
        _bm25_texts.append(text)
        _bm25_metadata.append({
            "id": str(i),
            "source_file": chunk["metadata"].get("source_file", ""),
            "page_number": chunk["metadata"].get("page_number", 1),
        })

    _bm25_corpus = BM25Okapi(tokenized)
    logger.info("BM25 index built: %d documents", len(_bm25_texts))


def _tokenize(text: str) -> List[str]:
    """中英混合分词"""
    # 英文: 按空白+标点切分
    # 中文: 按字符切 (简化, 生产用 jieba)
    tokens = []
    # 英文单词
    en_words = re.findall(r'[a-zA-Z0-9]+', text)
    tokens.extend(w.lower() for w in en_words)
    # 中文字符
    cn_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for seg in cn_chars:
        tokens.extend(list(seg))  # 逐字
    return tokens


def sparse_search(
    query: str,
    top_k: int = 20,
) -> List[dict]:
    """BM25 全文检索"""
    global _bm25_corpus, _bm25_texts, _bm25_metadata

    if _bm25_corpus is None:
        return []

    query_tokens = _tokenize(query)
    scores = _bm25_corpus.get_scores(query_tokens)

    # 按分数排序
    ranked = sorted(
        enumerate(scores),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    results = []
    for idx, score in ranked:
        if score > 0:
            results.append({
                "id": _bm25_metadata[idx]["id"],
                "text": _bm25_texts[idx],
                "score": round(float(score), 4),
                "source_file": _bm25_metadata[idx]["source_file"],
                "page_number": _bm25_metadata[idx]["page_number"],
            })

    return results
