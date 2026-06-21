"""Structured document loader with markdown-aware chunk metadata."""
import hashlib
import re
from pathlib import Path
from typing import List

SUPPORTED_SUFFIXES = {".md", ".txt", ".pdf", ".docx"}


def compute_chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _clean_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\x00", "")
    return text.strip()


def _infer_department(path: Path) -> str:
    name = path.name.lower()
    if "employee" in name or "handbook" in name:
        return "HR"
    if "compliance" in name or "policy" in name:
        return "Compliance"
    if "architecture" in name:
        return "Technology"
    if "technical" in name or "tech_" in name:
        return "Technology"
    if "security" in name:
        return "Information Security"
    return "General"


def _parse_markdown_sections(text: str) -> List[dict]:
    lines = text.splitlines()
    doc_title = ""
    stack: list[tuple[int, str]] = []
    current = None
    sections = []

    def flush():
        nonlocal current
        if not current:
            return
        body = "\n".join(current["body"]).strip()
        if body:
            sections.append(
                {
                    "doc_title": doc_title or current["section"],
                    "section": current["section"],
                    "section_path": " > ".join(current["path"]),
                    "text": body,
                }
            )
        current = None

    for raw_line in lines:
        line = raw_line.rstrip()
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            if not doc_title and level == 1:
                doc_title = title
            flush()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            current = {"section": title, "path": [item[1] for item in stack], "body": [line]}
        else:
            if current is None:
                current = {"section": "chunk-1", "path": [doc_title or "chunk-1"], "body": []}
            current["body"].append(line)

    flush()
    if not sections and text.strip():
        sections.append({"doc_title": doc_title or "Untitled", "section": "chunk-1", "section_path": "", "text": text.strip()})
    return sections


def _split_section(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def _load_markdown_or_text(file_path: Path) -> List[dict]:
    text = _clean_text(file_path.read_text(encoding="utf-8-sig"))
    sections = _parse_markdown_sections(text)
    chunks = []
    department = _infer_department(file_path)
    doc_type = file_path.suffix.lstrip(".")

    for section in sections:
        header = [f"Document: {section['doc_title']}"]
        if section["section_path"]:
            header.append(f"Section Path: {section['section_path']}")
        header.append(f"Department: {department}")
        header.append("")
        header.append("Content:")

        for part in _split_section(section["text"]):
            content = "\n".join(header + [part]).strip()
            chunks.append(
                {
                    "text": content,
                    "metadata": {
                        "source_file": file_path.name,
                        "page_number": 1,
                        "section": section["section"],
                        "section_path": section["section_path"],
                        "doc_title": section["doc_title"],
                        "department": department,
                        "doc_type": doc_type,
                        "chunk_hash": compute_chunk_hash(content),
                    },
                }
            )
    return chunks


def load_document(file_path: Path) -> List[dict]:
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported format: {suffix}")
    if suffix in {".md", ".txt"}:
        return _load_markdown_or_text(file_path)
    raise ValueError(f"Document type currently unsupported in rebuilt loader: {suffix}")


def load_all_documents(data_dir: Path) -> List[dict]:
    all_chunks = []
    for fp in sorted(data_dir.iterdir()):
        if fp.is_file() and fp.suffix.lower() in SUPPORTED_SUFFIXES:
            all_chunks.extend(load_document(fp))
    return all_chunks
