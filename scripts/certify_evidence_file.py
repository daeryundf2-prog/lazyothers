#!/usr/bin/env python3
"""certify_evidence_file.py - 웹 채증 산출물 인증기 (URL·시각·해시 결합).

playwright 등으로 캡처한 스크린샷·PDF를 증거로 쓰려면 "캡처 시각, 출처 URL,
파일 해시"가 한 기록에 묶여 있어야 한다. 캡처 직후 이 스크립트를 1회 실행해
채증 기록(JSON + 마크다운)을 만든다. 캡처 파일은 인증 후 원본 보존 원칙에
따라 수정하면 안 된다 — 수정하면 해시가 바뀌어 기록과 어긋난다.

Exit code:
    0 — 인증 기록 생성 완료
    2 — 실행 오류 (대상 파일 없음 등)

CLI:
    python scripts/certify_evidence_file.py 캡처1.png 캡처2.pdf \
        --url "https://example.com/post/123" --case "2024가합12345" \
        --output 채증기록.json --output-md 채증기록.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

CHUNK = 1 << 20


def _hash_file(path: str, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def certify(files: list[str], url: str, note: str, case_number: str) -> dict:
    """파일 목록을 해시·시각과 함께 묶어 채증 기록 dict를 만든다."""
    items: list[dict] = []
    for path in files:
        if not os.path.isfile(path):
            print(f"error: 파일 없음: {path}", file=sys.stderr)
            return {}
        st = os.stat(path)
        items.append({
            "file": os.path.abspath(path),
            "name": os.path.basename(path),
            "size": st.st_size,
            "sha256": _hash_file(path, "sha256"),
            "md5": _hash_file(path, "md5"),
            # 캡처 파일의 생성 시각(mtime)과 인증 시각(지금)을 구분해 기록한다.
            "file_mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
        })
    record = {
        "certified_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "case_number": case_number,
        "source_url": url,
        "note": note,
        "items": items,
    }
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True)
    record["record_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return record


def render_markdown(record: dict) -> str:
    lines = ["# 웹 채증 기록 (Capture Certification)\n"]
    lines.append(f"- **인증 시각(UTC):** {record['certified_at_utc']}")
    if record.get("case_number"):
        lines.append(f"- **사건번호:** {record['case_number']}")
    if record.get("source_url"):
        lines.append(f"- **출처 URL:** {record['source_url']}")
    if record.get("note"):
        lines.append(f"- **메모:** {record['note']}")
    lines.append("")
    lines.append("| 파일 | 크기 | SHA-256 | MD5 | 캡처 파일 생성 시각(UTC) |")
    lines.append("| :-- | ---: | :-- | :-- | :-- |")
    for it in record["items"]:
        lines.append(
            f"| {it['name']} | {it['size']:,} | `{it['sha256']}` | `{it['md5']}` | {it['file_mtime_utc']} |"
        )
    lines.append(f"\n**본 기록 SHA-256:** `{record['record_sha256']}`")
    lines.append("\n> 본 기록은 캡처 시점의 파일 해시를 증명한다. 캡처 파일을 편집하면 해시가 달라지므로, 채증 후 원본은 그대로 보존하고 대조용으로만 사용하십시오. 법원 제출용 표찰이 필요하면 `stamp_evidence.py`로 라벨을 인자하십시오(단, 스탬핑본은 해시가 다르므로 본 기록은 원본 기준이다).")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="웹 채증 산출물 인증기 — URL·시각·해시 결합 기록 생성")
    p.add_argument("files", nargs="+", help="인증할 캡처 파일 (스크린샷/PDF)")
    p.add_argument("--url", default="", help="캡처 출처 URL")
    p.add_argument("--note", default="", help="메모 (캡처 상황 설명 등)")
    p.add_argument("--case", default="", help="사건번호 (선택)")
    p.add_argument("--output", default="", help="채증 기록 JSON 저장 경로")
    p.add_argument("--output-md", default="", help="채증 기록 마크다운 저장 경로")
    args = p.parse_args(argv)

    record = certify(args.files, args.url, args.note, args.case)
    if not record:
        return 2

    md = render_markdown(record)
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    if args.output_md:
        os.makedirs(os.path.dirname(os.path.abspath(args.output_md)) or ".", exist_ok=True)
        with open(args.output_md, "w", encoding="utf-8") as f:
            f.write(md)
    if not args.output and not args.output_md:
        print(md)
    else:
        print(f"[OK] 채증 기록 생성: {len(record['items'])}건 (record_sha256={record['record_sha256'][:16]}...)")
    return 0


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    raise SystemExit(main())
