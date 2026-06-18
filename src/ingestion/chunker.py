"""
语义分块 - 按段落/标题边界切分，非固定长度
"""
import re
from typing import List


def semantic_chunk(text: str, chunk_size: int = 512, overlap: int = 100) -> List[str]:
    """按语义边界分块，保持 chunk 语义完整"""
    # 先按双换行分割（段落边界）
    paragraphs = re.split(r"\n\s*\n", text)

    chunks = []
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 如果是标题行（短行或以 # 开头），尝试作为新 chunk 起点
        is_heading = _is_heading_line(para)

        if is_heading and current:
            chunks.append(current.strip())
            current = para
            continue

        # 尝试追加
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
                # overlap: 保留上一段末尾
                overlap_text = current[-overlap:] if len(current) > overlap else current
                current = overlap_text + "\n\n" + para
            else:
                # 单段落就超长，硬切
                for i in range(0, len(para), chunk_size - overlap):
                    sub = para[i:i + chunk_size]
                    chunks.append(sub.strip())
                current = ""

    if current.strip():
        chunks.append(current.strip())

    # 过滤空 chunk
    return [c for c in chunks if len(c.strip()) > 10]


def _is_heading_line(text: str) -> bool:
    """判断是否为标题行"""
    if text.startswith("#"):
        return True
    # 短行（<60字符）且不以标点结尾 → 可能是标题
    if len(text) < 60 and not re.search(r'[。，；：、.!?,;:]$', text):
        # 包含数字编号如 "1. " "三、" 开头
        if re.match(r'^[\d一二三四五六七八九十]+[\.、\s]', text):
            return True
    return False
