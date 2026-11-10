#!/usr/bin/env python3
"""check_revision_residue.py - 수정 요청 반영 후 옛 값 잔존 검사.

소장·준비서면 등을 고친 뒤 당사자명·금액·날짜 같은 옛 문구가 본문, 표, 별지,
증거 목록, 사본 파일에 남았는지 찾는다. 공백 차이는 무시한다. 남은 hit는
--keep 으로 사유를 대지 않으면 설명 없는 잔존으로 보고 exit 1 을 낸다.
새 값은 --new 로 주면 각 파일에서 나타나는지도 센다(0건이면 경고만).

사용:
    py scripts/check_revision_residue.py 소장.md 별지/ --old "홍길동" --old "10,000,000원" \
        --new "홍길순" --keep "별지/연혁.md:3=개명 경위 설명"
Exit code: 0 잔존 없음 또는 전부 사유 있음 / 1 설명 없는 잔존 / 2 실행 오류

수정 요청 sweep 규칙의 뼈대는 hypercore(MIT, (c) 2026 alpoxdev)
hyper-feedback/rules/change-mapping.md 를 참고해 이 저장소 문서 체계에 맞게 다시 썼다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TEXT_SUFFIXES = {".md", ".txt", ".json", ".csv", ".tsv", ".html", ".htm", ".xml"}


def collect_files(paths):
    files, skipped = [], []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            candidates = sorted(p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            candidates = [path]
        else:
            raise FileNotFoundError(raw)
        for candidate in candidates:
            (files if candidate.suffix.lower() in TEXT_SUFFIXES else skipped).append(candidate)
    return files, skipped


def loose_pattern(needle):
    parts = [re.escape(ch) for ch in needle if not ch.isspace()]
    if not parts:
        raise ValueError("빈 검색어")
    return re.compile(r"\s*".join(parts))


def parse_keep(entries):
    keep = {}
    for entry in entries:
        location, sep, reason = entry.partition("=")
        path, colon, line = location.rpartition(":")
        if not sep or not colon or not line.isdigit() or not reason.strip():
            raise ValueError(f"--keep 형식은 경로:줄=사유 입니다: {entry}")
        keep[(str(Path(path)), int(line))] = reason.strip()
    return keep


def scan(files, olds, news, keep):
    old_patterns = [(text, loose_pattern(text)) for text in olds]
    new_patterns = [(text, loose_pattern(text)) for text in news]
    residues, kept, new_counts, unreadable = [], [], {text: 0 for text, _ in new_patterns}, []
    for path in files:
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append({"file": str(path), "error": type(exc).__name__})
            continue
        for number, line in enumerate(body.splitlines(), 1):
            for text, pattern in old_patterns:
                if pattern.search(line):
                    hit = {"file": str(path), "line": number, "old": text, "text": line.strip()[:120]}
                    reason = keep.get((str(path), number))
                    if reason:
                        kept.append({**hit, "reason": reason})
                    else:
                        residues.append(hit)
            for text, pattern in new_patterns:
                if pattern.search(line):
                    new_counts[text] += 1
    return residues, kept, new_counts, unreadable


def main(argv=None):
    parser = argparse.ArgumentParser(description="수정 후 옛 값 잔존 검사")
    parser.add_argument("paths", nargs="+", help="검사할 파일 또는 폴더")
    parser.add_argument("--old", action="append", required=True, help="사라져야 하는 옛 문구 (반복 가능)")
    parser.add_argument("--new", action="append", default=[], help="새로 나타나야 하는 문구 (반복 가능)")
    parser.add_argument("--keep", action="append", default=[], help="경로:줄=사유 — 의도적으로 남긴 곳")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        files, skipped = collect_files(args.paths)
        keep = parse_keep(args.keep)
        residues, kept, new_counts, unreadable = scan(files, args.old, args.new, keep)
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    warnings = [f"새 문구 '{text}' 이(가) 어느 파일에도 없음" for text, count in new_counts.items() if count == 0]
    warnings += [f"텍스트로 읽지 못한 파일: {item['file']}" for item in unreadable]
    warnings += [f"검사하지 않은 형식(HWPX·PDF 등은 변환 후 재검사): {path}" for path in skipped]
    result = {"verdict": "FAIL" if residues else "PASS", "residues": residues, "kept": kept,
              "new_counts": new_counts, "warnings": warnings, "files_scanned": len(files)}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[{result['verdict']}] 검사 파일 {len(files)}개, 설명 없는 잔존 {len(residues)}건, 사유 있는 유지 {len(kept)}건")
        for hit in residues:
            print(f"  잔존 {hit['file']}:{hit['line']} '{hit['old']}' | {hit['text']}")
        for hit in kept:
            print(f"  유지 {hit['file']}:{hit['line']} '{hit['old']}' | 사유: {hit['reason']}")
        for warning in warnings:
            print(f"  [WARN] {warning}")
    return 1 if residues else 0


if __name__ == "__main__":
    raise SystemExit(main())
