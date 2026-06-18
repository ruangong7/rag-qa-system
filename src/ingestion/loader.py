"""
文档加载器 - 支持 PDF (含扫描件 OCR)、Markdown、TXT、Word
"""
import hashlib
import logging
from pathlib import Path
from typing import List, Iterator

from unstructured.partition.auto import partition
import pdfplumber

from src.ingestion.chunker import semantic_chunk
from src.ingestion.ocr import ocr_page

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".docx"}


def compute_chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_document(file_path: Path) -> List[dict]:
    """加载单个文档，返回 chunk 列表"""
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported format: {suffix}")

    logger.info("loading document", path=str(file_path))

    if suffix == ".pdf":
        raw_chunks = _load_pdf(file_path)
    else:
        raw_chunks = _load_generic(file_path)

    # 语义分块
    chunks = []
    for raw in raw_chunks:
        sub_chunks = semantic_chunk(raw["text"], chunk_size=512, overlap=100)
        for sc in sub_chunks:
            chunks.append({
                "text": sc,
                "metadata": {
                    "source_file": file_path.name,
                    "page_number": raw.get("page", 1),
                    "doc_type": raw.get("doc_type", suffix.lstrip(".")),
                    "chunk_hash": compute_chunk_hash(sc),
                }
            })
    logger.info("document loaded", path=str(file_path), chunks=len(chunks))
    return chunks


def _load_pdf(file_path: Path) -> List[dict]:
    """PDF 加载，对扫描页走 OCR"""
    chunks = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and len(text.strip()) > 20:
                # 文本层有内容，直接使用
                chunks.append({"text": text.strip(), "page": i, "doc_type": "pdf"})
            else:
                # 可能是扫描件，走 OCR
                logger.info("scan detected, running OCR", page=i)
                ocr_text = ocr_page(file_path, i)
                if ocr_text.strip():
                    chunks.append({"text": ocr_text.strip(), "page": i, "doc_type": "scanned_pdf"})
    return chunks


def _load_generic(file_path: Path) -> List[dict]:
    """通过 unstructured 加载其他格式"""
    elements = partition(filename=str(file_path))
    text = "\n".join(str(e) for e in elements if str(e).strip())
    return [{"text": text, "page": 1, "doc_type": file_path.suffix.lstrip(".")}]


def load_all_documents(data_dir: Path) -> List[dict]:
    """加载目录下所有支持的文档"""
    all_chunks = []
    for fp in sorted(data_dir.iterdir()):
        if fp.suffix.lower() in SUPPORTED_SUFFIXES:
            all_chunks.extend(load_document(fp))
    return all_chunks
