#!/usr/bin/env python3
"""mask_korean_pii.py - 한국형 개인정보 자동 마스킹 (법원 제출본·공문서 비식별화).

텍스트에서 주민등록번호(체크섬 검증), 전화/휴대폰, 계좌번호, 이메일을 탐지해
마스킹한다. kordoc의 redact_document가 HWPX/HWP 원본 서식 보존 마스킹을 담당하므로,
이 스크립트는 텍스트·마크다운·CSV 레이어의 비식별화를 담당한다.

마스킹 규칙 (일반적인 공적 서식 관행):
    주민등록번호  901212-1******   (생년월일+성별코드 유지, 뒤 6자리 마스크)
    전화/휴대폰   02-123-**** / 010-1234-****   (말미 4자리 마스크)
    계좌번호      123-45-******   (앞 2그룹 유지, 나머지 마스크)
    이메일        h**@example.com   (로컬파트 첫 글자만 유지)

한계 (문서에 명시해야 한다): 사람 이름·주소는 사전 없이는 탐지할 수 없다.
이름 단위 비식별화가 필요하면 ko-pii(MIT) 같은 사전 기반 라이브러리를
보강으로 검토하라.

Exit code: 0 완료 / 2 실행 오류
CLI:
    python scripts/mask_korean_pii.py 증거설명서.md -o 제출용.md
    python scripts/mask_korean_pii.py 데이터.csv --types rrn,phone
"""

from __future__ import annotations

import argparse
import os
import re
import sys

# ── 주민등록번호 ────────────────────────────────────────────────────
# 6자리 생년월일 - 성별코드(1~4) + 일련. 유효 생월일만 후보로 잡아 오탐을 줄인다.
_RRN_RE = re.compile(
    r"\b(?P<birth>\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01]))"
    r"-(?P<sex>[1-4])(?P<rest>\d{6})\b"
)
_RRN_WEIGHTS = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)

# ── 전화/휴대폰 ─────────────────────────────────────────────────────
_PHONE_RE = re.compile(r"\b(02|0[3-6]\d|01[0136789]|070|050\d)-(\d{3,4})-(\d{4})\b")

# ── 계좌번호 (은행 무관 일반 3그룹 형식) ────────────────────────────
_ACCOUNT_RE = re.compile(r"\b(\d{3,6})-(\d{2,6})-(\d{2,6})\b")
# 날짜(2024-01-16)와 0으로 시작하는 번호판별 값은 계좌로 오탐하지 않는다.
_DATEISH_RE = re.compile(r"^(19|20)\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")

# ── 이메일 ──────────────────────────────────────────────────────────
_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")


def validate_rrn(rrn: str) -> bool:
    """주민등록번호 체크섬 검증. 형식 후보가 실제 유효한지 2차 확인용."""
    digits = rrn.replace("-", "")
    if len(digits) != 13:
        return False
    total = sum(int(d) * w for d, w in zip(digits[:12], _RRN_WEIGHTS))
    return (11 - total % 11) % 10 == int(digits[12])


def mask_text(text: str, types: set[str]) -> tuple[str, dict]:
    """텍스트를 마스킹하고 (마스킹본, 통계)를 반환한다."""
    stats: dict = {"rrn": 0, "rrn_bad_checksum": 0, "phone": 0, "account": 0, "account_skipped_date": 0, "email": 0}

    def _rrn(m: re.Match) -> str:
        candidate = m.group(0)
        stats["rrn"] += 1
        if not validate_rrn(candidate):
            # 체크섬이 틀려도 마스킹은 한다 — 틀린 번호가 개인정보가 아니라는 뜻이 아니다.
            stats["rrn_bad_checksum"] += 1
        return f"{m.group('birth')}-{m.group('sex')}******"

    if "rrn" in types:
        text = _RRN_RE.sub(_rrn, text)

    def _phone(m: re.Match) -> str:
        stats["phone"] += 1
        return f"{m.group(1)}-{m.group(2)}-****"

    if "phone" in types:
        text = _PHONE_RE.sub(_phone, text)

    def _account(m: re.Match) -> str:
        candidate = m.group(0)
        if _DATEISH_RE.match(candidate):
            stats["account_skipped_date"] += 1
            return candidate  # 날짜로 보임 — 손대지 않는다
        stats["account"] += 1
        return f"{m.group(1)}-{m.group(2)}-******"

    if "account" in types:
        text = _ACCOUNT_RE.sub(_account, text)

    def _email(m: re.Match) -> str:
        stats["email"] += 1
        return f"{m.group(1)}**@{m.group(2)}"

    if "email" in types:
        text = _EMAIL_RE.sub(_email, text)

    return text, stats


ALL_TYPES = {"rrn", "phone", "account", "email"}


def render_report(stats: dict, source: str) -> str:
    lines = ["## 비식별화 처리 결과\n"]
    lines.append(f"- **원본:** {source}")
    lines.append(f"- **주민등록번호:** {stats['rrn']}건 마스킹 (체크섬 불일치 {stats['rrn_bad_checksum']}건 — 형식만 맞는 값이 포함되어 있을 수 있으니 원본 확인 요망)")
    lines.append(f"- **전화/휴대폰:** {stats['phone']}건")
    lines.append(f"- **계좌번호:** {stats['account']}건 (날짜로 판별해 유지 {stats['account_skipped_date']}건)")
    lines.append(f"- **이메일:** {stats['email']}건")
    lines.append("\n> 사람 이름·주소는 이 도구가 탐지하지 못한다. 필요하면 사전 기반 도구(ko-pii 등)를 보강으로 사용하고, 최종 제출본은 사람이 1회 더 훑어야 한다.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="한국형 개인정보 자동 마스킹 (주민번호/전화/계좌/이메일)")
    p.add_argument("input", help="입력 텍스트/마크다운/CSV 파일")
    p.add_argument("--output", "-o", default="", help="마스킹본 저장 경로 (미지정 시 stdout)")
    p.add_argument("--report", default="", help="처리 결과 리포트 저장 경로 (선택)")
    p.add_argument("--types", default="rrn,phone,account,email", help="쉼표 구분: rrn,phone,account,email")
    args = p.parse_args(argv)

    types = {t.strip() for t in args.types.split(",") if t.strip()}
    unknown = types - ALL_TYPES
    if unknown:
        print(f"error: 알 수 없는 타입: {sorted(unknown)} (가능: {sorted(ALL_TYPES)})", file=sys.stderr)
        return 2
    if not os.path.isfile(args.input):
        print(f"error: 파일을 찾을 수 없습니다: {args.input}", file=sys.stderr)
        return 2

    with open(args.input, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    masked, stats = mask_text(text, types)
    report = render_report(stats, args.input)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(masked)
        print(f"[OK] 마스킹본 저장: {args.output}")
        if args.report:
            with open(args.report, "w", encoding="utf-8") as f:
                f.write(report + "\n")
        print(report, file=sys.stderr)
    else:
        print(masked)
        print("\n" + report, file=sys.stderr)
    return 0


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    raise SystemExit(main())
