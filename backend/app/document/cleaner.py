"""Text Cleaner：清洗提取出的文本。"""
import re

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_SPACES_RE = re.compile(r"[ \t]+")
_MULTI_BLANK_LINES_RE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """去控制字符、压缩空白、规范化空行。"""
    text = _CONTROL_CHARS_RE.sub("", text)
    text = _SPACES_RE.sub(" ", text)
    text = _MULTI_BLANK_LINES_RE.sub("\n\n", text)
    return text.strip()
