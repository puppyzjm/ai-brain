"""OCR 相关测试：扫描页检测（不依赖 AI API）。"""
import fitz  # PyMuPDF

from app.document.loader import find_empty_pages


def _make_text_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "This is a text page for testing.")
    doc.save(path)
    doc.close()


def _make_blank_pdf(path: str) -> None:
    """创建一页无文字层的 PDF（模拟扫描页）。"""
    doc = fitz.open()
    doc.new_page()  # 空白页：无文字层
    doc.save(path)
    doc.close()


def test_find_empty_pages_on_text_pdf(tmp_path) -> None:
    path = str(tmp_path / "text.pdf")
    _make_text_pdf(path)
    assert find_empty_pages(path) == []


def test_find_empty_pages_detects_blank_page(tmp_path) -> None:
    path = str(tmp_path / "blank.pdf")
    _make_blank_pdf(path)
    assert find_empty_pages(path) == [0]
