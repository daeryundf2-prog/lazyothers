"""stamp_evidence.py 회귀 테스트 — 한글 표찰이 깨지지 않는지 검증."""

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

fitz = pytest.importorskip("fitz", reason="pymupdf required")

import stamp_evidence  # noqa: E402

LABEL = "갑 제1호증"


def _norm(text: str) -> str:
    """PDF 폰트 셰이핑이 공백을 NBSP(\xa0)로 바꿀 수 있어 정규화."""
    return text.replace("\xa0", " ")


def _make_pdf(path: Path, pages: int = 2) -> Path:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(path)
    doc.close()
    return path


def test_korean_font_detection_or_skip():
    """한글 폰트가 있으면 경로를, 없으면 None을 반환한다(테스트는 폰트 없으면 skip)."""
    font = stamp_evidence._get_korean_font()
    if font is None:
        pytest.skip("Korean font not available on this machine")


def test_stamp_label_is_not_question_marks(tmp_path):
    """회귀: 폰트가 있을 때 한글 라벨이 '?'로 깨지면 안 된다."""
    font = stamp_evidence._get_korean_font()
    if font is None:
        pytest.skip("Korean font not available on this machine")

    src = _make_pdf(tmp_path / "src.pdf")
    out = tmp_path / "stamped.pdf"
    assert stamp_evidence.stamp_pdf_pymupdf(str(src), str(out), LABEL)

    doc = fitz.open(str(out))
    page0 = _norm(doc[0].get_text())
    doc.close()
    assert LABEL in page0, f"Korean label corrupted: {page0!r}"


def test_bates_numbering_all_pages(tmp_path):
    src = _make_pdf(tmp_path / "src.pdf", pages=2)
    out = tmp_path / "bates.pdf"
    assert stamp_evidence.stamp_pdf_pymupdf(str(src), str(out), LABEL, bates_prefix="P", start_page=1)

    doc = fitz.open(str(out))
    texts = [_norm(p.get_text()) for p in doc]
    doc.close()
    assert "P-0001" in texts[0]
    assert "P-0002" in texts[1]


def test_first_only_flag(tmp_path):
    src = _make_pdf(tmp_path / "src.pdf", pages=2)
    out = tmp_path / "first.pdf"
    assert stamp_evidence.stamp_pdf_pymupdf(str(src), str(out), LABEL, all_pages=False)

    doc = fitz.open(str(out))
    p0, p1 = _norm(doc[0].get_text()), _norm(doc[1].get_text())
    doc.close()
    assert LABEL in p0
    assert LABEL not in p1
