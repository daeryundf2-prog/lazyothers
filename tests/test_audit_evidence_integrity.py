"""audit_evidence_integrity.py 회귀 테스트 — 해시 감사·보고서 대조·증명서."""

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import audit_evidence_integrity as aei  # noqa: E402


@pytest.fixture()
def evidence(tmp_path):
    f1 = tmp_path / "증거1.pdf"
    f1.write_bytes(b"%PDF-1.4 evidence one")
    f2 = tmp_path / "증거2.hwp"
    f2.write_bytes(b"HWP binary evidence two")
    sub = tmp_path / "sub"
    sub.mkdir()
    f3 = sub / "증거3.png"
    f3.write_bytes(b"\x89PNG evidence three")
    return tmp_path, [str(f1), str(f2), str(f3)]


def test_collect_targets_recursive(evidence):
    tmp_path, expected = evidence
    got = aei.collect_targets(scan_dir=str(tmp_path))
    assert sorted(got) == sorted(expected)


def test_compute_hash_matches_hashlib(evidence):
    import hashlib
    _, files = evidence
    assert aei.compute_hash(files[0], "sha256") == hashlib.sha256(
        Path(files[0]).read_bytes()
    ).hexdigest()


def test_audit_verdicts_against_report(evidence):
    tmp_path, files = evidence
    correct = aei.compute_hash(files[0], "sha256")
    wrong = "0" * 64
    report = tmp_path / "증거설명서.md"
    report.write_text(
        f"# 증거설명서\n| 갑 제1호증 | 증거1.pdf | `{correct}` |\n"
        f"| 갑 제2호증 | 증거2.hwp | `{wrong}` |\n",
        encoding="utf-8",
    )
    result = aei.audit(files[:2], ["sha256"], report.read_text(encoding="utf-8"))
    verdicts = {Path(r["name"]).name: r["verdict"] for r in result["records"]}
    assert verdicts["증거1.pdf"] == "일치"
    assert verdicts["증거2.hwp"] == "불일치"
    assert result["summary"]["불일치"] == 1


def test_audit_unmentioned_file_is_unmeasured(evidence):
    tmp_path, files = evidence
    report = tmp_path / "r.md"
    report.write_text("# 증거설명서\n관련 내용 없음\n", encoding="utf-8")
    result = aei.audit(files, ["sha256"], report.read_text(encoding="utf-8"))
    assert all(r["verdict"] == "미측정" for r in result["records"])


def test_audit_without_report_only_measures(evidence):
    _, files = evidence
    result = aei.audit(files, ["sha256"], "")
    assert all(r["verdict"] == "산출" for r in result["records"])
    assert all(r["hashes"]["sha256"] for r in result["records"])


def test_main_exit_codes_and_markdown(evidence, capsys, monkeypatch):
    tmp_path, files = evidence
    correct = aei.compute_hash(files[0], "sha256")
    report = tmp_path / "증거설명서.md"
    report.write_text(f"| 갑 제1호증 | 증거1.pdf | `{correct}` |", encoding="utf-8")
    out_md = tmp_path / "감사보고서.md"

    rc = aei.main([
        "--file", files[0], "--report", str(report), "--output", str(out_md),
    ])
    assert rc == 0
    md = out_md.read_text(encoding="utf-8")
    assert "✅ 일치" in md
    assert "Chain of Custody Verification Sheet" in md
    assert "본 감사 기록 SHA-256" in md

    # 불일치 → exit 1
    wrong = "f" * 64
    report.write_text(f"| 갑 제1호증 | 증거1.pdf | `{wrong}` |", encoding="utf-8")
    rc = aei.main(["--file", files[0], "--report", str(report)])
    assert rc == 1

    # 대상 없음 → exit 2
    rc = aei.main([])
    assert rc == 2


def test_multi_algorithm_audit(evidence):
    _, files = evidence
    result = aei.audit(files[:1], ["sha256", "md5", "sha1"], "")
    hashes = result["records"][0]["hashes"]
    assert set(hashes) == {"sha256", "md5", "sha1"}
    assert len(hashes["sha256"]) == 64 and len(hashes["md5"]) == 32 and len(hashes["sha1"]) == 40


# ── 짝이변·TOCTOU 회귀 ──────────────────────────────────────────────

def test_swapped_hashes_detected_as_mismatch(tmp_path):
    # 보고서가 두 파일의 해시를 서로 바꿔 적은 경우 — 과거에는 둘 다 '일치'로
    # 통과했다. 파일명 근처의 해시로만 판정해야 짝이변이 잡힌다.
    a = tmp_path / "a.pdf"; a.write_bytes(b"AAA")
    b = tmp_path / "b.pdf"; b.write_bytes(b"BBB")
    ha = aei.compute_hash(str(a), "sha256")
    hb = aei.compute_hash(str(b), "sha256")
    report = (
        "| 파일 | SHA-256 |\n"
        f"| a.pdf | `{hb}` |\n"
        f"| b.pdf | `{ha}` |\n"
    )
    result = aei.audit([str(a), str(b)], ["sha256"], report)
    verdicts = {r["name"]: r["verdict"] for r in result["records"]}
    assert verdicts[str(a)] == "불일치", "짝이변은 불일치로 나와야 한다"
    assert verdicts[str(b)] == "불일치"


def test_correct_pairing_still_matches(tmp_path):
    a = tmp_path / "a.pdf"; a.write_bytes(b"AAA")
    ha = aei.compute_hash(str(a), "sha256")
    report = f"| 파일 | SHA-256 |\n| a.pdf | `{ha}` |\n"
    result = aei.audit([str(a)], ["sha256"], report)
    assert result["records"][0]["verdict"] == "일치"


def test_hash_present_without_filename_marked_caution(tmp_path):
    # 해시는 보고서에 있지만 파일명이 없으면 대응 미확인 — '주의'로 남긴다.
    a = tmp_path / "a.pdf"; a.write_bytes(b"AAA")
    ha = aei.compute_hash(str(a), "sha256")
    result = aei.audit([str(a)], ["sha256"], f"부록: `{ha}` (파일명 미기재)")
    assert result["records"][0]["verdict"] == "주의"
    assert result["summary"]["주의"] == 1
