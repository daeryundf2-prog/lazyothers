"""mask_korean_pii.py 회귀 테스트 — 체크섬·마스킹 규칙·날짜 오탐 방지."""

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import mask_korean_pii as mk  # noqa: E402

VALID_RRN = "901212-1234568"   # 체크섬 유효 (가상 인물)
INVALID_RRN = "901212-1234563"  # 형식은 맞지만 체크섬 불일치


def test_validate_rrn_checksum():
    assert mk.validate_rrn(VALID_RRN)
    assert not mk.validate_rrn(INVALID_RRN)
    assert not mk.validate_rrn("900212-123456")  # 자릿수 부족


def test_rrn_masked_regardless_of_checksum():
    text = f"갑: {VALID_RRN} 을: {INVALID_RRN}"
    masked, stats = mk.mask_text(text, {"rrn"})
    assert VALID_RRN not in masked and INVALID_RRN not in masked
    assert "901212-1******" in masked
    assert stats["rrn"] == 2 and stats["rrn_bad_checksum"] == 1


def test_phone_masking_keeps_prefix():
    masked, stats = mk.mask_text("연락처 010-1234-5678, 사무실 02-123-4567", {"phone"})
    assert "010-1234-****" in masked
    assert "02-123-****" in masked
    assert stats["phone"] == 2


def test_account_masked_but_dates_preserved():
    text = "계좌 123-45-678901, 지급일 2024-01-16"
    masked, stats = mk.mask_text(text, {"account"})
    assert "123-45-******" in masked
    assert "2024-01-16" in masked, "날짜가 계좌번호로 오탐되면 안 된다"
    assert stats["account"] == 1 and stats["account_skipped_date"] == 1


def test_email_masked():
    masked, stats = mk.mask_text("메일: hong.gildong@example.com", {"email"})
    assert "h**@example.com" in masked
    assert "hong.gildong" not in masked
    assert stats["email"] == 1


def test_type_filtering():
    text = f"주민번호 {VALID_RRN}, 메일 a@b.com"
    masked, stats = mk.mask_text(text, {"phone"})
    assert VALID_RRN in masked, "미선택 유형은 원본 유지되어야 한다"
    assert "a@b.com" in masked
    assert stats["rrn"] == 0


def test_full_pipeline_all_types():
    text = f"901212-1234561 / 010-1234-5678 / 123-45-678901 / x@y.co.kr / 2024-01-16"
    masked, _ = mk.mask_text(text, mk.ALL_TYPES)
    for original in (VALID_RRN, "010-1234-5678", "123-45-678901", "x@y.co.kr"):
        assert original not in masked
    assert "2024-01-16" in masked


def test_main_writes_output_and_report(tmp_path):
    src = tmp_path / "input.md"
    src.write_text(f"주민번호 {VALID_RRN}", encoding="utf-8")
    out = tmp_path / "masked.md"
    report = tmp_path / "report.md"
    assert mk.main([str(src), "-o", str(out), "--report", str(report)]) == 0
    assert "901212-1******" in out.read_text(encoding="utf-8")
    assert "체크섬" in report.read_text(encoding="utf-8")
    assert mk.main([str(src), "--types", "bogus"]) == 2
