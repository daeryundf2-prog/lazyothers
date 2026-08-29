#!/usr/bin/env python3
"""audit_evidence_integrity.py - 디지털 증거 해시 무결성 감사기.

대상 파일(폴더 전수 또는 파일 목록)의 해시를 계산하고, 제출용 보고서
마크다운에 기재된 해시값과 대조해 [일치 / 불일치 / 미측정] 판정표와
무결성 증명서(Chain of Custody Verification Sheet)를 마크다운으로 산출한다.

판정 규칙 (보고서 대조 시)
    일치   — 계산된 해시가 보고서 텍스트에 그대로 존재한다
    불일치 — 보고서가 이 파일명을 언급하며 같은 길이의 해시를 근처에 기재했는데
             계산값과 다르다 (사고 후보 — 원본 교체·파손·기재 오류)
    미측정 — 보고서에서 이 파일을 찾을 수 없다 (측정 누락)

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


def verdict_for(entry: dict, report_text: str, report_hashes: dict[str, set[str]]) -> str:
    """파일 1건의 판정. entry = {name, hashes: {algo: value}}."""
    base = os.path.basename(entry["name"])
    if not report_text:
        return "산출"
    windows = [m.start() for m in re.finditer(re.escape(base), report_text)]
    for algo, value in entry["hashes"].items():
        if value in report_hashes[algo]:
            return "일치"
    if not windows:
        return "미측정"
    # 파일명이 언급됐다 — 언급 근처에 같은 길이 해시가 있으면 그것이 '기재된 해시'다.
    for pos in windows:
        lo, hi = max(0, pos - _CONTEXT_WINDOW), pos + _CONTEXT_WINDOW
        near = report_text[lo:hi]
        for algo, value in entry["hashes"].items():
            claimed = [m.group(0).lower() for m in _HASH_RE[algo].finditer(near)]
            if claimed and value not in claimed:
                return "불일치"
    return "미측정"


def audit(targets: list[str], algorithms: list[str], report_text: str = "") -> dict:
    records: list[dict] = []
    report_hashes = extract_report_hashes(report_text) if report_text else {}
    for path in targets:
        if not os.path.isfile(path):
            records.append({"name": path, "error": "파일 없음", "verdict": "불일치"})
            continue
        entry = {
            "name": path,
            "size": os.path.getsize(path),
            "hashes": {a: compute_hash(path, a) for a in algorithms},
        }
        entry["verdict"] = verdict_for(entry, report_text, report_hashes)
        records.append(entry)
    summary = {v: sum(1 for r in records if r["verdict"] == v) for v in ("일치", "불일치", "미측정", "산출")}
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
        mark = {"일치": "✅ 일치", "불일치": "❌ 불일치", "미측정": "⚠️ 미측정", "산출": "🔍 산출"}[r["verdict"]]
        lines.append(f"| {r['name']} | {r['size']:,} | {cells} | {mark} |")

    s = result["summary"]
    mismatched = [r for r in result["records"] if r["verdict"] == "불일치"]
    lines.append(f"\n**요약:** 일치 {s.get('일치', 0)} · 불일치 {s.get('불일치', 0)} · 미측정 {s.get('미측정', 0)} · 산출 {s.get('산출', 0)}\n")
    if mismatched:
        lines.append("### 불일치 상세 — 제출 전 해소 필수\n")
        for r in mismatched:
            lines.append(f"- `{r['name']}`: 계산값과 보고서 기재값이 다릅니다. 원본 교체·파손·기재 오류 중 무엇인지 원본 대조로 확인하십시오.")

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
