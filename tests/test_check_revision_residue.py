"""check_revision_residue.py 회귀 테스트 — 수정 후 옛 값 잔존 검사."""

import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import check_revision_residue as crr


@pytest.fixture()
def draft(tmp_path):
    body = tmp_path / "소장.md"
    body.write_text("원고 홍길순은 피고에게 10,000,000원을 청구한다.\n", encoding="utf-8")
    annex = tmp_path / "별지"
    annex.mkdir()
    (annex / "증거목록.md").write_text("갑 제1호증 홍 길 동 차용증\n", encoding="utf-8")
    return tmp_path


def test_clean_draft_passes(draft, capsys):
    (draft / "별지" / "증거목록.md").write_text("갑 제1호증 홍길순 차용증\n", encoding="utf-8")
    assert crr.main([str(draft), "--old", "홍길동", "--new", "홍길순"]) == 0
    assert "PASS" in capsys.readouterr().out


def test_residue_in_annex_fails_even_with_spacing(draft, capsys):
    assert crr.main([str(draft), "--old", "홍길동"]) == 1
    out = capsys.readouterr().out
    assert "증거목록.md:1" in out


def test_kept_hit_with_reason_passes(draft, capsys):
    target = draft / "별지" / "증거목록.md"
    assert crr.main([str(draft), "--old", "홍길동", "--keep", f"{target}:1=개명 전 증거명"]) == 0
    assert "개명 전 증거명" in capsys.readouterr().out


def test_keep_without_reason_is_usage_error(draft):
    assert crr.main([str(draft), "--old", "홍길동", "--keep", f"{draft}/별지/증거목록.md:1="]) == 2


def test_missing_new_value_warns_without_failing(draft, capsys):
    (draft / "별지" / "증거목록.md").write_text("정리됨\n", encoding="utf-8")
    assert crr.main([str(draft), "--old", "홍길동", "--new", "없는값", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert any("없는값" in warning for warning in result["warnings"])


def test_unscanned_binary_format_is_reported(draft, capsys):
    (draft / "사본.hwpx").write_bytes(b"PK\x03\x04")
    assert crr.main([str(draft), "--old", "홍길동", "--keep", f"{draft}/별지/증거목록.md:1=사유", "--json"]) == 0
    assert any("사본.hwpx" in warning for warning in json.loads(capsys.readouterr().out)["warnings"])


def test_missing_path_is_usage_error(tmp_path):
    assert crr.main([str(tmp_path / "없음.md"), "--old", "x"]) == 2
