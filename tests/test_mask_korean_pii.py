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


# ── 조사 접착 회귀 (P0: \b 경계는 한국어 조사에서 탐지를 실패했다) ──────

def test_rrn_masked_with_particle_attached():
    # "1234568임을"처럼 조사가 띄어쓰기 없이 붙어도 잡혀야 한다 —
    # 실제 판결문/공문서에서 가장 흔한 문장형이다.
    text = f"주민등록번호가 {VALID_RRN}임을 확인하였다."
    masked, stats = mk.mask_text(text, {"rrn"})
    assert VALID_RRN not in masked
    assert "901212-1******임을 확인하였다." in masked
    assert stats["rrn"] == 1


def test_phone_masked_with_particle_attached():
    masked, stats = mk.mask_text("피고는 010-1234-5678으로 전화하였다.", {"phone"})
    assert "010-1234-****으로" in masked
    assert stats["phone"] == 1


def test_account_masked_with_particle_attached():
    masked, stats = mk.mask_text("계좌 123-45-678901에서 송금하였다.", {"account"})
    assert "123-45-******에서" in masked
    assert stats["account"] == 1


def test_email_masked_with_particle_attached():
    masked, stats = mk.mask_text("회신은 hong@example.com으로 주시기 바랍니다.", {"email"})
    assert "h**@example.com으로" in masked
    assert stats["email"] == 1


def test_longer_digit_run_not_masked_as_rrn():
    # 더 긴 숫자열의 일부는 주민번호로 잡지 않는다.
    masked, stats = mk.mask_text("등록번호 901212-12345689 는 14자리다", {"rrn"})
    assert stats["rrn"] == 0
    assert "901212-12345689" in masked


# ── 외국인등록번호 (성별코드 5~8) ──────────────────────────────────

def test_foreigner_number_masked():
    text = "외국인등록번호 901212-5678901와 880301-7654321가 있다"
    masked, stats = mk.mask_text(text, {"rrn"})
    assert "901212-5******" in masked
    assert "880301-7******" in masked
    assert stats["rrn"] == 2


def test_foreigner_number_masked_with_particle():
    masked, _ = mk.mask_text("등록번호는 901212-5678901이다.", {"rrn"})
    assert "901212-5******이다." in masked


# ── 인코딩 (CP949 손실 방지) ────────────────────────────────────────

def test_cp949_input_masked_and_encoding_preserved(tmp_path):
    src = tmp_path / "bank.csv"
    src.write_bytes(f"이름,주민번호,연락처\n홍길동,{VALID_RRN},010-1234-5678\n".encode("cp949"))
    out = tmp_path / "masked.csv"
    assert mk.main([str(src), "-o", str(out)]) == 0
    decoded = out.read_bytes().decode("cp949")
    assert "홍길동" in decoded, "CP949 본문이 U+FFFD로 훼손되면 안 된다"
    assert "901212-1******" in decoded
    assert "010-1234-****" in decoded


def test_utf8_bom_input_preserved(tmp_path):
    src = tmp_path / "bom.md"
    src.write_bytes(b"\xef\xbb\xbf" + f"주민번호 {VALID_RRN}".encode("utf-8"))
    out = tmp_path / "masked.md"
    assert mk.main([str(src), "-o", str(out)]) == 0
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")
    assert "901212-1******" in out.read_text(encoding="utf-8-sig")


def test_undecodable_input_fails_closed(tmp_path):
    # 어느 인코딩으로도 읽지 못하면 U+FFFD로 유실하는 대신 실패해야 한다.
    src = tmp_path / "broken.bin"
    src.write_bytes(b"\x80\x80\x80\x80")  # utf-8 연속 바이트, cp949 리드 바이트 범위 밖
    assert mk.main([str(src), "-o", str(tmp_path / "out.txt")]) == 2
