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


def test_provisional_remedy_and_family_codes_pass():
    text = (
        "채권자는 서울중앙지방법원 2024카단12345 가압류 결정 및 "
        "서울가정법원 2023느단67890 상속한정승인 심판, 수원회생법원 2023개회55555 결정을 원용합니다."
    )
    res = vlf.verify_legal_text(text)
    assert res["verdict"] == "PASS"
    assert len(res["warnings"]) == 0
    assert "2024카단12345" in res["cited_precedents"]
    assert "2023느단67890" in res["cited_precedents"]
    assert "2023개회55555" in res["cited_precedents"]


def test_statute_branch_articles_preserved_and_bounded():
    valid_text = "개인정보보호법 제76조의2 과징금 및 정보통신망법 제44조의7 불법정보 유통금지."
    res_valid = vlf.verify_legal_text(valid_text)
    assert res_valid["verdict"] == "PASS"
    assert "개인정보보호법 제76조의2" in res_valid["cited_statutes"]
    assert "정보통신망법 제44조의7" in res_valid["cited_statutes"]

    invalid_text = "개인정보보호법 제99조의2 위반."
    res_invalid = vlf.verify_legal_text(invalid_text)
    assert res_invalid["verdict"] == "FAIL"
    assert any("개인정보보호법" in e and "제99조의2" in e for e in res_invalid["errors"])


def test_specialized_courts_recognized():
    text = "헌법재판소 2020헌바123 결정 및 특허법원 2022허4567 판결."
    res = vlf.verify_legal_text(text)
    assert res["verdict"] == "PASS"
    assert len(res["errors"]) == 0
    assert len(res["warnings"]) == 0
    assert "2020헌바123" in res["cited_precedents"]
    assert "2022허4567" in res["cited_precedents"]


def test_legal_factuality_guard_target_file_key(tmp_path):
    import subprocess
    guard_script = SCRIPT_DIR / "legal_factuality_guard.mjs"
    bad_file = tmp_path / "소장_테스트.md"
    bad_file.write_text("피고는 민법 제1500조에 따라 원고에게 지급하라.", encoding="utf-8")

    # Pass TargetFile key as JSON payload
    payload = json.dumps({"TargetFile": str(bad_file), "CodeContent": "..."})
    proc = subprocess.run(
        ["node", str(guard_script)],
        input=payload,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    # Guard should catch the target file and fail-closed (exit code 1)
    assert proc.returncode == 1
    assert "민법" in proc.stderr or "LEGAL FACTUALITY GUARD" in proc.stderr


def test_flexible_spacing_statute_names_checked():
    # Spaced statute names (official spacing like 개인정보 보호법) must be caught
    text_pii = "피고는 개인정보 보호법 제100조를 위반하였다."
    res_pii = vlf.verify_legal_text(text_pii)
    assert res_pii["verdict"] == "FAIL"
    assert any("개인정보" in e and "제100조" in e for e in res_pii["errors"])

    text_labor = "근로 기준법 제120조에 기한 청구."
    res_labor = vlf.verify_legal_text(text_labor)
    assert res_labor["verdict"] == "FAIL"
    assert any("근로기준법" in e and "제120조" in e for e in res_labor["errors"])

    text_secret = "부정경쟁방지 및 영업비밀 보호에 관한 법률 제20조 위반."
    res_secret = vlf.verify_legal_text(text_secret)
    assert res_secret["verdict"] == "FAIL"
    assert any("부정경쟁방지" in e and "제20조" in e for e in res_secret["errors"])


def test_legal_factuality_guard_file_key(tmp_path):
    import subprocess
    guard_script = SCRIPT_DIR / "legal_factuality_guard.mjs"
    bad_file = tmp_path / "답변서_검토.md"
    bad_file.write_text("원고의 주장은 형사 소송법 제500조에 비추어 타당하지 않습니다.", encoding="utf-8")

    # Pass filename key as JSON payload
    payload = json.dumps({"filename": str(bad_file)})
    proc = subprocess.run(
        ["node", str(guard_script)],
        input=payload,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 1
    assert "형사소송법" in proc.stderr or "LEGAL FACTUALITY GUARD" in proc.stderr


def test_abolished_and_fabricated_courts_blocked():
    text1 = "서울민사지방법원 2021가단100 판결을 원용합니다."
    res1 = vlf.verify_legal_text(text1)
    assert res1["verdict"] == "FAIL"
    assert any("서울민사지방법원" in e and "법원 명칭 날조" in e for e in res1["errors"])

    text2 = "한국연방법원 2023가합500 소송 계속 중입니다."
    res2 = vlf.verify_legal_text(text2)
    assert res2["verdict"] == "FAIL"
    assert any("한국연방법원" in e and "법원 명칭 날조" in e for e in res2["errors"])


def test_evidence_tag_attribution_and_grounding():
    source_facts = "2024년 1월 16일 원고는 피고에게 금 10,000,000원을 무통장 송금하였다."

    # Matching quote passes
    draft_valid = (
        "<evidence>2024년 1월 16일 원고는 피고에게 금 10,000,000원을 무통장 송금하였다.</evidence>\n"
        "피고는 원고로부터 대여금을 수령하였습니다."
    )
    res_valid = vlf.verify_legal_text(draft_valid, source_text=source_facts)
    assert res_valid["verdict"] == "PASS"

    # Fabricated quote fails verbatim match
    draft_invalid = (
        "<evidence>2024년 5월 20일 피고가 전액 상환하겠다고 각서를 작성하였다.</evidence>\n"
        "피고는 채무를 승인하였습니다."
    )
    res_invalid = vlf.verify_legal_text(draft_invalid, source_text=source_facts)
    assert res_invalid["verdict"] == "FAIL"
    assert any("근거 인용 불일치" in e for e in res_invalid["errors"])

    # Empty evidence tag fails
    draft_empty = "<evidence>   </evidence>\n소장 내용."
    res_empty = vlf.verify_legal_text(draft_empty)
    assert res_empty["verdict"] == "FAIL"
    assert any("비어 있습니다" in e for e in res_empty["errors"])




