"""certify_evidence_file.py 회귀 테스트 — 채증 기록의 해시·시각·URL 결합."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import certify_evidence_file as cef  # noqa: E402


@pytest.fixture()
def capture(tmp_path):
    f = tmp_path / "캡처.png"
    f.write_bytes(b"\x89PNG fake screenshot bytes")
    return f


def test_certify_binds_hash_url_and_time(capture):
    rec = cef.certify([str(capture)], url="https://example.com/p/1", note="본문 캡처", case_number="2024가합1")
    assert rec["items"][0]["sha256"] == hashlib.sha256(capture.read_bytes()).hexdigest()
    assert rec["source_url"] == "https://example.com/p/1"
    assert rec["case_number"] == "2024가합1"
    assert rec["certified_at_utc"].endswith("+00:00")
    assert rec["items"][0]["file_mtime_utc"].endswith("+00:00")


def test_record_self_hash_deterministic(capture):
    rec1 = cef.certify([str(capture)], url="u", note="", case_number="")
    rec2 = cef.certify([str(capture)], url="u", note="", case_number="")
    # certified_at이 다르면 자기 해시도 달라진다(기록 시각이 다른 별개 기록)
    assert rec1["record_sha256"] == rec2["record_sha256"] or rec1["certified_at_utc"] == rec2["certified_at_utc"]
    payload = {k: v for k, v in rec1.items() if k != "record_sha256"}
    assert rec1["record_sha256"] == hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def test_missing_file_returns_empty(capture):
    assert cef.certify([str(capture), "없는파일.png"], "", "", "") == {}


def test_main_outputs_json_and_markdown(capture, tmp_path):
    out_json = tmp_path / "채증기록.json"
    out_md = tmp_path / "채증기록.md"
    rc = cef.main([
        str(capture), "--url", "https://example.com/x",
        "--output", str(out_json), "--output-md", str(out_md),
    ])
    assert rc == 0
    rec = json.loads(out_json.read_text(encoding="utf-8"))
    assert rec["items"][0]["name"] == "캡처.png"
    md = out_md.read_text(encoding="utf-8")
    assert "웹 채증 기록" in md
    assert hashlib.sha256(capture.read_bytes()).hexdigest() in md
    assert "record_sha256" in md or "본 기록 SHA-256" in md


def test_main_missing_file_exit_2():
    assert cef.main(["없는파일.png"]) == 2
