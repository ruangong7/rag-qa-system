"""
OCR 模块 - PaddleOCR 封装
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_ocr_instance = None


def get_ocr(lang_list=None):
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        if lang_list is None:
            lang_list = ["ch", "en"]
        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="ch",
            show_log=False,
        )
    return _ocr_instance


def ocr_page(pdf_path: Path, page_num: int) -> str:
    """对 PDF 某一页做 OCR"""
    try:
        ocr = get_ocr()
        # 将 PDF 页转为图片
        from pdf2image import convert_from_path
        images = convert_from_path(
            str(pdf_path),
            first_page=page_num,
            last_page=page_num,
            dpi=200,
        )
        if not images:
            return ""

        import numpy as np
        img_array = np.array(images[0])
        result = ocr.ocr(img_array, cls=True)

        lines = []
        if result and result[0]:
            for line in result[0]:
                if line and len(line) >= 2:
                    text = line[1][0] if isinstance(line[1], (list, tuple)) else line[1]
                    lines.append(text)

        return "\n".join(lines)
    except Exception as e:
        logger.warning("OCR failed", page=page_num, error=str(e))
        return ""
