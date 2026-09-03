"""test_verify_legal_factuality.py — 법률 환각 검증기(verify_legal_factuality.py) 단위 테스트."""

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import verify_legal_factuality as vlf


def test_valid_statute_and_precedent_pass():
    text = """
    # 준비서면
    원고는 민법 제390조(채무불이행) 및 제750조(불법행위)에 기하여 손해배상을 청구합니다.
    대법원 2017다220744 판결 및 2018도13792 판결의 법리에 따릅니다.
    변호사의 검토 후 제출 바랍니다. AI 생성 초안입니다.
    """
    res = vlf.verify_legal_text(text)
    assert res["verdict"] == "PASS"
    assert len(res["errors"]) == 0
    assert "민법 제390조" in res["cited_statutes"]
    assert "2017다220744" in res["cited_precedents"]


def test_statute_out_of_bounds_detected():
    text = "피고의 행위는 민법 제1500조 및 형법 제500조에 위반됩니다."
    res = vlf.verify_legal_text(text)
    assert res["verdict"] == "FAIL"
    assert any("민법" in e and "제1500조" in e for e in res["errors"])
    assert any("형법" in e and "제500조" in e for e in res["errors"])


def test_future_precedent_year_blocked():
    text = "대법원 2099다12345 판결에 따라 원고의 청구는 이유 있다."
    res = vlf.verify_legal_text(text, current_year=2026)
    assert res["verdict"] == "FAIL"
    assert any("미래 연도 판결" in e and "2099다12345" in e for e in res["errors"])


def test_pre_1948_precedent_blocked():
    text = "대법원 1910다100 판결을 인용한다."
    res = vlf.verify_legal_text(text)
    assert res["verdict"] == "FAIL"
    assert any("1948년 이전" in e for e in res["errors"])


def test_unusual_case_code_warns():
    text = "서울중앙지방법원 2024쀍9999 판결 참조."
    res = vlf.verify_legal_text(text)
    assert res["verdict"] == "WARN"
    assert any("비표준 사건부호" in w for w in res["warnings"])


def test_cli_execution_with_temp_file(tmp_path):
    f = tmp_path / "draft.md"
    f.write_text("민법 제750조 손해배상. 대법원 2021다274214 판결.", encoding="utf-8")
    res = vlf.verify_legal_file(str(f))
    assert res["verdict"] == "PASS"
    assert "2021다274214" in res["cited_precedents"]
