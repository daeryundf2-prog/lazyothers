"""humanize eval 스위트 회귀 테스트 — 누락됐던 모듈·픽스처 계약을 잠근다.

eval_baseline.py는 humanize_asserts·humanize_runner·tests/fixtures.json을
요구하지만 60c2c59(humanize 통합 커밋)에 이 셋이 포함되지 않아 스크립트가
전혀 동작하지 않았다. 이 테스트는 그 계약을 다시 깨지 않도록 검증한다.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "skills" / "humanize-korean" / "references"
for _p in (str(REFS), str(ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import humanize_asserts as ha  # noqa: E402
import humanize_runner as hr  # noqa: E402
import metrics_v2  # noqa: E402
import eval_baseline  # noqa: E402
import eval_compare  # noqa: E402

FIXTURES = json.loads((ROOT / "tests" / "fixtures.json").read_text(encoding="utf-8"))["fixtures"]


# ── humanize_asserts: 신호 디스패치 ────────────────────────────────


def test_signal_dispatch_counts_known_patterns():
    assert ha.signal("결론적으로 다시 말하면 따라서 이르므로", "conclusion_pivot_count") >= 2
    assert ha.signal("양쪽 모두를 언급하며 균형을 말했다", "safe_balance_count") == 2
    # metrics_v2가 '되어진다'와 그 부분열 '되어진'을 각각 세므로 2가 맞다
    assert ha.signal("규정에 의해 제한되어진다", "double_passive_count") >= 1
    assert ha.signal("시스템에 의해 사용되어진 결과", "by_passive_count") == 1
    assert ha.signal("우리는 두 가지 질문을 가지고 있다", "have_make_literal_count") == 1
    assert ha.signal("데이터에서의 손실과 경험으로의 전환", "double_particle_count") == 2


def test_signal_returns_zero_for_clean_text():
    text = FIXTURES[3]["input_text"]
    for name in ha.SIGNALS:
        assert ha.signal(text, name) == 0, name


def test_signal_rejects_unknown_name_instead_of_returning_zero():
    with pytest.raises(ValueError):
        ha.signal("아무 텍스트", "conclusion_pivot_typo")


def test_change_rate_delegates_to_metrics_v2_ssot():
    same = "같은 문장이다. 바뀌지 않았다."
    assert ha.change_rate(same, same) == 0.0
    changed = "완전히 다른 내용으로 바뀌었을 때의 문장이다."
    assert ha.change_rate(same, changed) > 0
    assert ha.change_rate(same, changed) == metrics_v2.change_rate(same, changed)


def test_missing_protected_tokens_reports_only_missing():
    out = "2026년 기준 사용률은 30%다."
    assert ha.missing_protected_tokens(out, ["2026년", "30%"]) == []
    assert ha.missing_protected_tokens(out, ["2026년", "GPT-5"]) == ["GPT-5"]
    assert ha.missing_protected_tokens(out, []) == []


def test_missing_protected_tokens_survives_josa_attachment():
    """보호 토큰은 조사가 붙어 재등장해도 보존된 것으로 본다(「2026년」→「2026년의»)."""
    assert ha.missing_protected_tokens("2026년의 보고서", ["2026년"]) == []


# ── humanize_asserts: register 판정 ───────────────────────────────


def test_register_formal_polite_plain():
    formal = "본 보고서는 개정 흐름을 검토합니다. 제재 체계를 요약합니다. 기록을 관리할 필요가 있습니다."
    polite = "사흘을 보내고 돌아왔어요. 파도 소리가 먼저 들렸어요. 몸으로 남기로 했거든요."
    plain = "여행은 기억을 재편하는 작업이다. 장면은 정리된 모습이 된다. 우리는 이를 인정해야 한다."
    assert ha.register_of(formal) == "formal"
    assert ha.register_of(polite) == "polite"
    assert ha.register_of(plain) == "plain"


def test_register_mixed_and_unknown():
    mixed = "검토합니다. 돌아왔어요. 인정해야 한다."
    assert ha.register_of(mixed) == "mixed"
    assert ha.register_of("사과 바나나 귤") == "unknown"


# ── tests/fixtures.json 계약 ──────────────────────────────────────


def test_fixtures_contract():
    assert FIXTURES, "픽스처가 비어 있다"
    for fx in FIXTURES:
        assert fx["id"] and fx["input_text"].strip()
        assert fx["genre"] in {"essay", "column", "report", "blog", "abstract"}
        # 불변식: 보호 토큰은 원문에 실제로 존재해야 한다
        assert not ha.missing_protected_tokens(fx["input_text"], fx["protected_tokens"]), fx["id"]


def test_ai_fixtures_fire_signals_and_clean_fixture_does_not():
    signal_names = list(ha.SIGNALS)
    for fx in FIXTURES:
        total = sum(ha.signal(fx["input_text"], n) for n in signal_names)
        if fx["id"].startswith("human_"):
            assert total == 0, f"{fx['id']}: 클린 픽스처에 AI 신호 {total}개"
        else:
            assert total > 0, f"{fx['id']}: AI 신호가 전혀 걸리지 않음"


# ── eval_baseline: dry-run·집계 ───────────────────────────────────


def test_eval_baseline_dry_run_loads_fixtures():
    """회귀: fixtures.json·모듈 임포트가 살아 있으면 dry-run은 0으로 끝난다."""
    assert eval_baseline.main(["--dry-run"]) == 0


def test_eval_baseline_aggregate_computes_noise_floor():
    runs = [
        {"ok": True, "metrics": {
            "change_rate": 0.1, "len_ratio": 1.0,
            "sig_conclusion_pivot_count_out": 2,
            "missing_protected": [], "register_preserved": True}},
        {"ok": True, "metrics": {
            "change_rate": 0.3, "len_ratio": 1.2,
            "sig_conclusion_pivot_count_out": 4,
            "missing_protected": ["GPT-5"], "register_preserved": False}},
        {"ok": False, "error": "RuntimeError: boom", "metrics": {}},
    ]
    agg = eval_baseline.aggregate(runs)
    assert agg["n_ok"] == 2 and agg["n_fail"] == 1
    assert agg["change_rate"]["mean"] == 0.2
    assert agg["change_rate"]["stdev"] > 0  # 잡음 바닥이 기록되어야 비교가 가능하다
    assert agg["protected_ok_rate"] == 0.5
    assert agg["register_preserved_rate"] == 0.5


# ── eval_compare: 판정 규칙 ───────────────────────────────────────


def test_eval_compare_verdict_rules():
    assert eval_compare.verdict(0.0, 0.0, 2.0) == "동일"
    assert eval_compare.verdict(0.5, 0.0, 2.0) == "판정불가"
    assert eval_compare.verdict(0.1, 0.2, 2.0) == "잡음"
    assert eval_compare.verdict(1.0, 0.2, 2.0) == "유의"


def test_eval_compare_direction_lower_is_better():
    agg_a = {"sig_conclusion_pivot_count_out": {"mean": 2.0, "stdev": 0.5, "n": 3}}
    agg_b = {"sig_conclusion_pivot_count_out": {"mean": 0.0, "stdev": 0.5, "n": 3}}
    r = eval_compare.compare_metric(agg_a, agg_b, "sig_conclusion_pivot_count_out", 2.0)
    assert r["verdict"] == "유의" and r["direction"] == "개선"


def _snapshot(tmp_path, name, mean, stdev):
    snap = {
        "label": name, "captured_at": "2026-08-29T00:00:00+00:00",
        "git_commit": "deadbee", "k": 3, "strict": False,
        "models": ["claude-sonnet-5"], "fixtures": ["ai_essay_standard"],
        "signal_names": ["conclusion_pivot_count"],
        "aggregates": {"claude-sonnet-5": {"ai_essay_standard": {
            "sig_conclusion_pivot_count_out": {
                "mean": mean, "stdev": stdev, "min": mean, "max": mean, "n": 3},
            "protected_ok_rate": 1.0,
        }}},
    }
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_eval_compare_end_to_end_json(tmp_path, capsys):
    before = _snapshot(tmp_path, "before", 3.0, 0.5)
    after = _snapshot(tmp_path, "after", 1.0, 0.5)
    rc = eval_compare.main([before, after, "--json"])
    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    sig = [r for r in rows if r["metric"] == "sig_conclusion_pivot_count_out"]
    assert sig and sig[0]["verdict"] == "유의" and sig[0]["direction"] == "개선"


# ── humanize_runner: 러너 계약 ────────────────────────────────────


def test_run_humanize_requires_binary(monkeypatch):
    monkeypatch.setattr(hr, "CLAUDE_BIN", None)
    with pytest.raises(RuntimeError):
        hr.run_humanize("원문")


def test_run_humanize_strips_summary_block_and_prompt_carries_rules(monkeypatch):
    monkeypatch.setattr(hr, "CLAUDE_BIN", "fake-claude")
    captured = {}

    def fake_exec(cmd, timeout):
        captured["cmd"] = cmd
        return 0, "윤문된 본문입니다.\n<!-- HUMANIZE-SUMMARY {\"x\": 1} -->\n", ""

    monkeypatch.setattr(hr, "_exec", fake_exec)
    out = hr.run_humanize("원문 텍스트", model="claude-sonnet-5")
    assert out == "윤문된 본문입니다."
    assert "HUMANIZE-SUMMARY" not in out
    prompt = captured["cmd"][2]  # [bin, "-p", prompt, "--model", model]
    assert "원문 텍스트" in prompt
    assert "의미 불변" in prompt  # 최상위 규율
    assert "문체 등급" in prompt  # register 보존
    assert captured["cmd"][captured["cmd"].index("--model") + 1] == "claude-sonnet-5"


def test_run_humanize_strict_adds_diagnosis_instruction(monkeypatch):
    monkeypatch.setattr(hr, "CLAUDE_BIN", "fake-claude")
    prompts = []

    def fake_exec(cmd, timeout):
        prompts.append(cmd[2])
        return 0, "결과", ""

    monkeypatch.setattr(hr, "_exec", fake_exec)
    hr.run_humanize("원문", strict=False)
    hr.run_humanize("원문", strict=True)
    assert "정밀 모드" not in prompts[0]
    assert "정밀 모드" in prompts[1]


def test_run_humanize_raises_on_failure(monkeypatch):
    monkeypatch.setattr(hr, "CLAUDE_BIN", "fake-claude")
    monkeypatch.setattr(hr, "_exec", lambda c, t: (1, "", "boom"))
    with pytest.raises(RuntimeError, match="종료 코드"):
        hr.run_humanize("원문")
    monkeypatch.setattr(hr, "_exec", lambda c, t: (0, "   ", ""))
    with pytest.raises(RuntimeError, match="비어"):
        hr.run_humanize("원문")
