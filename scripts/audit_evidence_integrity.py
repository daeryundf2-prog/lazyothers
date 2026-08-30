#!/usr/bin/env python3
"""audit_evidence_integrity.py - 디지털 증거 해시 무결성 감사기.

대상 파일(폴더 전수 또는 파일 목록)의 해시를 계산하고, 제출용 보고서
마크다운에 기재된 해시값과 대조해 [일치 / 불일치 / 미측정] 판정표와
무결성 증명서(Chain of Custody Verification Sheet)를 마크다운으로 산출한다.

판정 규칙 (보고서 대조 시)
    일치   — 파일명 언급 근처에 계산된 해시가 그대로 기재되어 있다
    불일치 — 파일명 근처에 같은 길이의 해시가 기재됐는데 계산값과 다르다
             (사고 후보 — 원본 교체·파손·기재 오류·파일↔해시 짝이변)
    주의   — 파일명이 언급되지 않았지만 계산 해시가 보고서 어딘가에 존재한다
             (해시↔파일 대응이 확인되지 않았다 — 짝이변 여부 사람이 확인)
    미측정 — 보고서에서 이 파일과 그 해시를 찾을 수 없다 (측정 누락)

Exit code:
    0 — 불일치 없음
    1 — 불일치 존재 (법원 제출 전 반드시 해소)
    2 — 실행 오류 (대상 없음 등)

CLI:
    python scripts/audit_evidence_integrity.py --scan-dir 증거폴더 --report 증거설명서.md -o 감사보고서.md
    python scripts/audit_evidence_integrity.py --file a.pdf --file b.pdf --algorithms sha256,md5
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timezone

# 보고서에서 해시로 보이는 문자열. 알고리즘별 길이로 식별한다.
_HASH_RE = {
    "sha256": re.compile(r"\b[a-fA-F0-9]{64}\b"),
    "sha1": re.compile(r"\b[a-fA-F0-9]{40}\b"),
    "md5": re.compile(r"\b[a-fA-F0-9]{32}\b"),
}
# 파일명 언급 주변에서 대조할 반경(문자). 보고서 표·목록의 인접 셀을 커버한다.
_CONTEXT_WINDOW = 400

CHUNK = 1 << 20


def compute_hash(path: str, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def collect_targets(scan_dir: str = "", files: list[str] | None = None) -> list[str]:
    """스캔 대상 파일 목록. 폴더면 재귀 전수, 파일 지정이면 그대로."""
    targets: list[str] = []
    if scan_dir:
        for root, _dirs, names in os.walk(scan_dir):
            for name in names:
                targets.append(os.path.join(root, name))
    for f in files or []:
        if f not in targets:
            targets.append(f)
    return sorted(targets)


def extract_report_hashes(report_text: str) -> dict[str, set[str]]:
    """보고서에서 알고리즘별 해시 후보를 모두 뽑아 소문자 집합으로 반환."""
    out: dict[str, set[str]] = {}
    for algo, rx in _HASH_RE.items():
        out[algo] = {m.group(0).lower() for m in rx.finditer(report_text)}
    return out


def _line_bounds(lines: list[str]) -> list[tuple[int, int]]:
    """splitlines() 한 줄들이 원문에서 차지하는 [시작, 끝) 오프셋."""
    bounds: list[tuple[int, int]] = []
    off = 0
    for ln in lines:
        bounds.append((off, off + len(ln)))
        off += len(ln) + 1  # 개행 1바이트
    return bounds


def verdict_for(entry: dict, report_text: str, report_hashes: dict[str, set[str]]) -> str:
    """파일 1건의 판정. entry = {name, hashes: {algo: value}}.

    근거는 '파일명이 기재된 같은 줄의 해시'다. 보고서 전역 존재나 넓은
    근방 윈도우로 일치를 주면 두 파일의 해시를 서로 바꿔 적은 보고서
    (짝이변)가 둘 다 '일치'로 통과해버린다 — 교차 기재는 이 함수가 잡는
    핵심 사고다. 같은 줄에 해시가 없을 때만 근방 윈도우로 폴백하되, 근방에
    같은 길이 해시가 여러 개면 짝이 확정되지 않았으므로 '주의'로 남긴다.
    """
    base = os.path.basename(entry["name"])
    if not report_text:
        return "산출"
    if base not in report_text:
        for algo, value in entry["hashes"].items():
            if value in report_hashes[algo]:
                return "주의"
        return "미측정"

    lines = report_text.splitlines()
    bounds = _line_bounds(lines)
    mention_lines: set[int] = set()
    mention_pos: list[int] = []
    for m in re.finditer(re.escape(base), report_text):
        mention_pos.append(m.start())
        for i, (lo, hi) in enumerate(bounds):
            if lo <= m.start() <= hi:
                mention_lines.add(i)
                break

    def claims_on(idx: int, algo: str) -> list[str]:
        return [x.group(0).lower() for x in _HASH_RE[algo].finditer(lines[idx])]

    # 1) 같은 줄 판정 — 표·목록에서 해시는 파일명과 같은 줄에 기재된다.
    for algo, value in entry["hashes"].items():
        for i in mention_lines:
            if value in claims_on(i, algo):
                return "일치"
    for algo, value in entry["hashes"].items():
        for i in mention_lines:
            claimed = claims_on(i, algo)
            if claimed and value not in claimed:
                return "불일치"
    # 2) 근방 폴백 — 해시가 파일명 줄이 아닌 바로 다음 줄 등에 있을 때.
    for pos in mention_pos:
        lo, hi = max(0, pos - _CONTEXT_WINDOW), pos + _CONTEXT_WINDOW
        near = report_text[lo:hi]
        for algo, value in entry["hashes"].items():
            claimed = [x.group(0).lower() for x in _HASH_RE[algo].finditer(near)]
            unique = set(claimed)
            if not unique:
                continue
            if value in unique:
                # 근방에 해시가 여러 종류면 이 파일과 짝지어졌다고 단정할 수 없다.
                return "일치" if len(unique) == 1 else "주의"
            return "불일치"
    # 3) 근방에 해시가 전혀 없다 — 계산값이 보고서 어딘가에만 있으면 대응 미확인.
    for algo, value in entry["hashes"].items():
        if value in report_hashes[algo]:
            return "주의"
    return "미측정"


def audit(targets: list[str], algorithms: list[str], report_text: str = "") -> dict:
    records: list[dict] = []
    report_hashes = extract_report_hashes(report_text) if report_text else {}
    for path in targets:
        if not os.path.isfile(path):
            records.append({"name": path, "error": "파일 없음", "verdict": "불일치"})
            continue
        # 감사 도중 파일이 바뀌면 해시가 무의미해진다 — 읽기 전후 메타데이터
        # 를 대조해 변경을 감지하면 명시적으로 실패 처리한다 (TOCTOU 방어).
        stat_before = os.stat(path)
        entry = {
            "name": path,
            "size": stat_before.st_size,
            "hashes": {a: compute_hash(path, a) for a in algorithms},
        }
        stat_after = os.stat(path)
        if (stat_before.st_size, stat_before.st_mtime_ns) != (stat_after.st_size, stat_after.st_mtime_ns):
            entry = {"name": path, "error": "감사 중 파일 변경 감지 — 해시 무효", "verdict": "불일치"}
            records.append(entry)
            continue
        entry["verdict"] = verdict_for(entry, report_text, report_hashes)
        records.append(entry)
    summary = {v: sum(1 for r in records if r["verdict"] == v) for v in ("일치", "불일치", "주의", "미측정", "산출")}
    return {"records": records, "summary": summary}


def render_markdown(result: dict, algorithms: list[str], report_path: str, audit_time: str) -> str:
    lines: list[str] = []
    lines.append("# 증거 무결성 감사 보고서\n")
    lines.append(f"- **감사 시각(UTC):** {audit_time}")
    lines.append(f"- **대상 파일:** {len(result['records'])}건")
    lines.append(f"- **알고리즘:** {', '.join(algorithms)}")
    lines.append(f"- **대조 보고서:** {report_path or '(미지정 — 산출만 수행)'}\n")

    lines.append("## 판정표\n")
    lines.append("| 파일 | 크기 | " + " | ".join(a.upper() for a in algorithms) + " | 판정 |")
    lines.append("| :-- | ---: | " + " | ".join(["---"] * len(algorithms)) + " | :--: |")
    for r in result["records"]:
        if "error" in r:
            lines.append(f"| {r['name']} | - | " + " | ".join(["-"] * len(algorithms)) + f" | ❓ {r['error']} |")
            continue
        cells = " | ".join(f"`{r['hashes'][a]}`" for a in algorithms)
        mark = {"일치": "✅ 일치", "불일치": "❌ 불일치", "주의": "🟡 주의(대응 미확인)", "미측정": "⚠️ 미측정", "산출": "🔍 산출"}[r["verdict"]]
        lines.append(f"| {r['name']} | {r['size']:,} | {cells} | {mark} |")

    s = result["summary"]
    mismatched = [r for r in result["records"] if r["verdict"] == "불일치"]
    lines.append(f"\n**요약:** 일치 {s.get('일치', 0)} · 불일치 {s.get('불일치', 0)} · 주의 {s.get('주의', 0)} · 미측정 {s.get('미측정', 0)} · 산출 {s.get('산출', 0)}\n")
    if mismatched:
        lines.append("### 불일치 상세 — 제출 전 해소 필수\n")
        for r in mismatched:
            lines.append(f"- `{r['name']}`: 계산값과 보고서 기재값이 다릅니다. 원본 교체·파손·기재 오류·파일↔해시 짝이변 중 무엇인지 원본 대조로 확인하십시오.")
    cautioned = [r for r in result["records"] if r["verdict"] == "주의"]
    if cautioned:
        lines.append("### 주의 상세 — 해시↔파일 대응이 확인되지 않음\n")
        for r in cautioned:
            lines.append(f"- `{r['name']}`: 계산 해시가 보고서 어딘가에 존재하지만 파일명 근처에 기재되어 있지 않습니다. 보고서가 해시와 파일을 올바르게 짝지었는지 사람이 확인하십시오.")

    # Chain of Custody Verification Sheet
    self_payload = json.dumps(
        {"records": [{k: r.get(k) for k in ("name", "size", "hashes")} for r in result["records"]],
         "audit_time": audit_time},
        ensure_ascii=False, sort_keys=True,
    )
    self_hash = hashlib.sha256(self_payload.encode("utf-8")).hexdigest()
    lines.append("\n## Chain of Custody Verification Sheet\n")
    lines.append("| 항목 | 값 |")
    lines.append("| :-- | :-- |")
    lines.append(f"| 감사 대상 | {len(result['records'])}건 / {sum(r.get('size', 0) for r in result['records']):,} bytes |")
    lines.append(f"| 감사 시각 (UTC) | {audit_time} |")
    lines.append(f"| 감사 도구 | audit_evidence_integrity.py (lazyothers) |")
    lines.append(f"| 대조 보고서 | {report_path or '-'} |")
    lines.append(f"| 본 감사 기록 SHA-256 | `{self_hash}` |")
    lines.append("\n> 본 증명서는 감사 시점의 파일 해시를 기록한 것입니다. 이후 원본이 변경되면 해시가 달라지므로, 원본은 변경 없이 보존하고 감사 기록과 함께 보관하십시오.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="디지털 증거 해시 무결성 감사기 (일치/불일치/미측정 판정 + 무결성 증명서)")
    p.add_argument("--scan-dir", default="", help="재귀 전수 해시할 증거 폴더")
    p.add_argument("--file", action="append", default=[], help="개별 파일 지정 (반복 가능)")
    p.add_argument("--report", default="", help="대조할 제출용 보고서 마크다운 (증거설명서 등)")
    p.add_argument("--algorithms", default="sha256", help="쉼표 구분: sha256,sha1,md5 (기본 sha256)")
    p.add_argument("--output", "-o", default="", help="감사 보고서 저장 경로 (미지정 시 stdout)")
    args = p.parse_args(argv)

    algorithms = [a.strip().lower().replace("-", "") for a in args.algorithms.split(",") if a.strip()]
    unknown = [a for a in algorithms if a not in _HASH_RE]
    if unknown:
        print(f"error: 지원하지 않는 알고리즘: {unknown} (sha256, sha1, md5)", file=sys.stderr)
        return 2

    targets = collect_targets(args.scan_dir, args.file)
    if not targets:
        print("error: 대상이 없습니다. --scan-dir 또는 --file을 지정하십시오.", file=sys.stderr)
        return 2

    report_text = ""
    if args.report:
        if not os.path.isfile(args.report):
            print(f"error: 보고서를 찾을 수 없습니다: {args.report}", file=sys.stderr)
            return 2
        with open(args.report, "r", encoding="utf-8", errors="replace") as f:
            report_text = f.read()

    audit_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = audit(targets, algorithms, report_text)
    md = render_markdown(result, algorithms, args.report, audit_time)

    if args.output:
        out_dir = os.path.dirname(os.path.abspath(args.output))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[OK] 감사 보고서 저장: {args.output}")
    else:
        print(md)

    if result["summary"].get("불일치", 0):
        print(f"[FAIL] 불일치 {result['summary']['불일치']}건 — 제출 전 해소 필수", file=sys.stderr)
        return 1
    print("[OK] 불일치 없음")
    return 0


import json  # noqa: E402  (증명서 자체 해시 페이로드용 — 하단 임포트는 기존 관례 유지)

# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
# Windows(cp949)에서 한글·em-dash 출력이 UnicodeEncodeError 로 죽는 것을 막는다.
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    raise SystemExit(main())
