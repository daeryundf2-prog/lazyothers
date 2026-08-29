"""generate_legal_draft.py 회귀 테스트 — 문서 구조·증거 자동 인용·고지 강제."""

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import generate_legal_draft as gld  # noqa: E402

BASE = {
    "type": "소장",
    "case_info": {"court": "서울중앙지방법원", "plaintiff": "홍길동", "defendant": "주식회사 XXX"},
    "claims": ["대여금 원금 10,000,000원 및 지연손해금"],
    "facts": [
        {
            "heading": "1. 대여 관계의 성립",
            "paragraphs": ["원고는 2024년 1월 16일 피고에게 금 10,000,000원을 전달하였다(갑제1호증)."],
        },
        {
            "heading": "2. 변제 기한 경과",
            "paragraphs": ["피고는 변제 기한인 2024년 3월 1일까지 변제하지 않았다."],
            "evidence": ["갑 제2호증"],
        },
    ],
    "evidence_list": [
        {"label": "갑 제1호증", "title": "차용증"},
        {"label": "갑 제2호증", "title": "내용증명"},
    ],
}


def test_sojang_structure_and_watermark():
    md = gld.generate(BASE)
    assert "청구취지" in md and "청구원인" in md and "구하건은" in md
    assert gld.DISCLAIMER in md, "변호사 검토 고지는 항상 포함되어야 한다"
    assert "서울중앙지방법원" in md
    assert "증거 목록" in md and "차용증" in md


def test_evidence_auto_citation_normalizes_compact_label():
    """'갑제1호증'(붙여 씀)도 자동 탐지해 표준형 라벨+서증명으로 결합한다."""
    md = gld.generate(BASE)
    assert "*입증방법: 갑 제1호증, 차용증*" in md
    assert "*입증방법: 갑 제2호증, 내용증명*" in md


def test_unknown_label_reports_missing_title():
    data = json.loads(json.dumps(BASE))
    data["facts"][1]["evidence"] = ["갑 제9호증"]
    md = gld.generate(data)
    assert "갑 제9호증" in md and "(서증명 미기재)" in md


def test_all_document_types_render():
    for doc_type, must_contain in {
        "준비서면": ["답변의 요지", "기각"],
        "고소장": ["범죄사실", "고소 취지"],
        "내용증명": ["경위", "14일 이내"],
    }.items():
        data = json.loads(json.dumps(BASE))
        data["type"] = doc_type
        md = gld.generate(data)
        for token in must_contain:
            assert token in md, f"{doc_type}에 '{token}' 누락"
        assert gld.DISCLAIMER in md


def test_invalid_type_rejected():
    data = json.loads(json.dumps(BASE))
    data["type"] = "이혼소장"
    with pytest.raises(ValueError):
        gld.generate(data)


def test_main_writes_file_and_exit_codes(tmp_path):
    src = tmp_path / "draft.json"
    src.write_text(json.dumps(BASE, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "소장_초안.md"
    assert gld.main(["--input-json", str(src), "--output", str(out)]) == 0
    assert gld.DISCLAIMER in out.read_text(encoding="utf-8")

    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    assert gld.main(["--input-json", str(bad)]) == 2
    assert gld.main(["--input-json", "없음.json"]) == 2
