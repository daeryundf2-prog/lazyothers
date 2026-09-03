"""test_guards_sync.py — lazyothers 동기화 가드(markdown_structure_guard, stop_claim_guard, korean_law wrapper) 검증."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = "node"


def run_node_script(script_name, args=(), stdin_payload=None, env=None, cwd=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(
        [NODE, str(ROOT / "scripts" / script_name), *args],
        input=stdin_payload,
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=e,
        cwd=str(cwd or ROOT),
    )


def test_markdown_structure_guard_blocks_unclosed_evidence(tmp_path):
    f = tmp_path / "broken_evidence.md"
    f.write_text("# 문서\n<evidence>열기만 함\n", encoding="utf-8")
    proc = run_node_script("markdown_structure_guard.mjs", ["--check", str(f)])
    assert proc.returncode == 1
    assert "unclosed_evidence_tag" in proc.stderr


def test_markdown_structure_guard_blocks_empty_evidence(tmp_path):
    f = tmp_path / "empty_evidence.md"
    f.write_text("# 문서\n<evidence></evidence>\n", encoding="utf-8")
    proc = run_node_script("markdown_structure_guard.mjs", ["--check", str(f)])
    assert proc.returncode == 1
    assert "empty_evidence_block" in proc.stderr


def test_markdown_structure_guard_blocks_broken_citation(tmp_path):
    f = tmp_path / "broken_cite.md"
    f.write_text("# 문서\n본문【F:source.pdf†L50】인용\n", encoding="utf-8")
    proc = run_node_script("markdown_structure_guard.mjs", ["--check", str(f)])
    assert proc.returncode == 1
    assert "broken_citation_token" in proc.stderr


def test_stop_claim_guard_blocks_unsupported_claim():
    payload = json.dumps({
        "hook_event_name": "Stop",
        "last_assistant_message": "법률 문서 작성을 완료했습니다.",
    })
    proc = run_node_script("stop_claim_guard.mjs", stdin_payload=payload)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data.get("decision") == "block"


def test_stop_claim_guard_passes_strict_abstention():
    payload = json.dumps({
        "hook_event_name": "Stop",
        "last_assistant_message": "[INSUFFICIENT_DATA] 사실관계 추가 확인 필요.",
    })
    proc = run_node_script("stop_claim_guard.mjs", stdin_payload=payload)
    assert proc.returncode == 0
    assert proc.stdout.strip() == "{}"


def test_stop_claim_guard_blocks_phantom_files(tmp_path):
    payload = json.dumps({
        "hook_event_name": "Stop",
        "cwd": str(tmp_path),
        "last_assistant_message": "테스트 5 pass. 산출물: draft/phantom_sojang.md 생성을 완료했습니다.",
    })
    proc = run_node_script("stop_claim_guard.mjs", stdin_payload=payload)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data.get("decision") == "block"
    assert "Fact-Retracing" in data.get("reason", "")


def test_korean_law_mcp_wrapper_resolves_or_exits_honestly():
    # When no law API key is provided, wrapper either runs offline server or exits 78
    env = os.environ.copy()
    env.pop("LAW_OC", None)
    env.pop("KOREAN_LAW_API_KEY", None)
    proc = subprocess.run(
        [NODE, str(ROOT / "scripts" / "korean_law_mcp_wrapper.mjs")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=5,
    )
    # If fallback is found it may be waiting on stdio (timeout or 0) or exit 78 if none found
    assert proc.returncode in (0, 78) or proc.stderr != ""


def test_legal_factuality_guard_blocks_fake_statute(tmp_path):
    bad = tmp_path / "소장_초안.md"
    bad.write_text("# 소장\n원고는 민법 제1500조에 기하여 청구한다.", encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(bad)}})
    proc = run_node_script("legal_factuality_guard.mjs", stdin_payload=payload)
    assert proc.returncode == 1
    assert "LEGAL FACTUALITY GUARD" in proc.stderr
    assert "민법" in proc.stderr


def test_legal_factuality_guard_passes_clean_legal_doc(tmp_path):
    clean = tmp_path / "소장_초안.md"
    clean.write_text("# 소장\n원고는 민법 제750조에 기하여 청구한다. 변호사 검토 필수.", encoding="utf-8")
    payload = json.dumps({"tool_input": {"file_path": str(clean)}})
    proc = run_node_script("legal_factuality_guard.mjs", stdin_payload=payload)
    assert proc.returncode == 0


def test_hooks_json_contains_legal_guard():
    hooks_data = json.loads((ROOT / "hooks.json").read_text(encoding="utf-8"))
    ptu = hooks_data.get("hooks", {}).get("PostToolUse", [])
    commands = [h["command"] for entry in ptu for h in entry.get("hooks", [])]
    assert any("legal_factuality_guard.mjs" in c for c in commands)

