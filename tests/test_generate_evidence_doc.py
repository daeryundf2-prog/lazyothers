"""generate_evidence_doc.py 테스트 — 전체 SHA-256 기재 및 경로 해석 검증."""

import hashlib
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import generate_evidence_doc as ged  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_full_sha256_and_relative_path_resolution(tmp_path):
    """파일 경로가 input-json 기준 상대경로여도 전체 해시가 계산되어야 한다."""
    evidence_file = tmp_path / "증거.pdf"
    evidence_file.write_bytes(b"%PDF-1.4 fake evidence bytes")

    input_json = tmp_path / "evidence.json"
    input_json.write_text(
        f'''{{
          "evidence_list": [
            {{"label": "갑 제1호증", "title": "테스트 증거", "file_path": "증거.pdf"}}
          ]
        }}''',
        encoding="utf-8",
    )

    output = tmp_path / "증거설명서.md"
    ged.main(["--input-json", str(input_json), "--output", str(output), "--case-num", "2024가합1"])

    md = output.read_text(encoding="utf-8")
    full_hash = _sha256(evidence_file)
    assert full_hash in md, "전체 SHA-256이 기재되어야 함"
    assert "2024가합1" in md


def test_missing_file_marks_na(tmp_path):
    input_json = tmp_path / "evidence.json"
    input_json.write_text(
        '{"evidence_list": [{"label": "갑 제2호증", "title": "없는 파일", "file_path": "없음.pdf"}]}',
        encoding="utf-8",
    )
    output = tmp_path / "증거설명서.md"
    ged.main(["--input-json", str(input_json), "--output", str(output)])
    md = output.read_text(encoding="utf-8")
    assert "N/A (file not found)" in md


def test_explicit_sha256_respected(tmp_path):
    input_json = tmp_path / "evidence.json"
    input_json.write_text(
        '{"evidence_list": [{"label": "갑 제3호증", "title": "수동 해시", "sha256": "abc123"}]}',
        encoding="utf-8",
    )
    output = tmp_path / "증거설명서.md"
    ged.main(["--input-json", str(input_json), "--output", str(output)])
    md = output.read_text(encoding="utf-8")
    assert "abc123" in md


def test_sample_generation_carries_submission_ban_watermark(tmp_path):
    """회귀: 실제 증거 JSON 없이 생성하면 본문에 제출 금지 워터마크가 들어가야 한다."""
    output = tmp_path / "증거설명서.md"
    ged.main(["--output", str(output)])
    md = output.read_text(encoding="utf-8")
    assert "법원 제출 금지" in md, "샘플 문서에 워터마크 배너가 없음"
    assert "[SAMPLE]" in md


def test_real_input_has_no_watermark(tmp_path):
    """실제 증거 JSON으로 생성한 문서에는 워터마크가 없어야 한다."""
    input_json = tmp_path / "evidence.json"
    input_json.write_text(
        '{"evidence_list": [{"label": "갑 제1호증", "title": "실제 증거", "sha256": "deadbeef"}]}',
        encoding="utf-8",
    )
    output = tmp_path / "증거설명서.md"
    ged.main(["--input-json", str(input_json), "--output", str(output)])
    md = output.read_text(encoding="utf-8")
    assert "법원 제출 금지" not in md


def test_malformed_json_falls_back_to_sample_instead_of_crash(tmp_path):
    """회귀: JSON 파싱 실패 시 트레이스백 크래시 대신 샘플+워터마크로 진행한다."""
    input_json = tmp_path / "broken.json"
    input_json.write_text("{ not valid json !!", encoding="utf-8")
    output = tmp_path / "증거설명서.md"
    ged.main(["--input-json", str(input_json), "--output", str(output)])
    md = output.read_text(encoding="utf-8")
    assert "법원 제출 금지" in md
