#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_legal_factuality.py — Korean Legal and Precedent Hallucination Verifier.

Audits legal drafts, court ruling analyses, and legal documents against:
1. Statutory boundary bounds (e.g., Civil Act max article 1118, Criminal Act max 372).
2. Precedent format validity and year bounds (e.g., blocking future years or nonsense codes).
3. Grounding citations (warning on ungrounded legal claims without source references).

Directly addresses Section 5.1 & 5.2 of gemini_hallucination_mitigation_deep_dive.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Max article numbers for major Korean codes (as of 2026)
STATUTE_BOUNDS = {
    "민법": 1118,
    "형법": 372,
    "개인정보보호법": 76,
    "정보통신망법": 76,
    "정보통신망 이용촉진 및 정보보호 등에 관한 법률": 76,
    "상법": 935,
    "민사소송법": 502,
    "형사소송법": 493,
    "행정소송법": 46,
    "근로기준법": 116,
    "부정경쟁방지법": 18,
    "부정경쟁방지 및 영업비밀보호에 관한 법률": 18,
    "전자문서법": 37,
    "전자문서 및 전자거래 기본법": 37,
    "특정금융정보법": 22,
    "특정 금융거래정보의 보고 및 이용 등에 관한 법률": 22,
    "전자상거래법": 45,
    "전자상거래 등에서의 소비자보호에 관한 법률": 45,
    "자본시장법": 449,
    "자본시장과 금융투자업에 관한 법률": 449,
    "신용정보법": 53,
    "신용정보의 이용 및 보호에 관한 법률": 53,
    "소비자기본법": 86,
    "가사소송법": 72,
    "특허법": 232,
    "저작권법": 142,
}

def _make_statute_pattern(statute_name: str) -> re.Pattern:
    clean_name = re.sub(r"\s+", "", statute_name)
    escaped_chars = [re.escape(c) for c in clean_name]
    pattern_str = r"\s*".join(escaped_chars) + r"\s*제\s*(\d+)\s*조(?:\s*의\s*(\d+))?"
    return re.compile(pattern_str)

# Standard Korean court precedent symbol categories
VALID_CASE_CODES = {
    # 민사
    "가단", "가합", "가소", "나", "다", "라", "마", "그", "바", "자", "차",
    # 보전처분 / 민사신청
    "카", "카단", "카합", "카기", "카담", "카조", "카열", "카경",
    # 형사
    "고단", "고합", "고약", "노", "도", "로", "모", "오", "보", "코",
    # 가사소송 및 가사비송
    "드", "드단", "드합", "르", "르단", "르합", "므", "스", "으",
    "느", "느단", "느합", "즈", "즈단", "즈합",
    # 도산 / 회생 / 파산
    "회단", "회합", "회개", "개회", "개단", "개합", "하단", "하합", "하면", "개확",
    # 행정 / 특허
    "구", "구합", "구단", "누", "두", "루", "무", "허",
    # 헌법재판소
    "헌가", "헌나", "헌다", "헌라", "헌마", "헌바", "헌사", "헌아",
    # 소년보호
    "푸", "버",
    # 재심
    "재가단", "재가합", "재다", "재나", "재도", "재노", "재고단", "재고합",
}

PRECEDENT_RE = re.compile(
    r"\b(?P<court>대법원|헌법재판소|특허법원|[가-힣]{2,6}가정법원|[가-힣]{2,6}행정법원|[가-힣]{2,6}고등법원|서울중앙지방법원|[가-힣]{2,6}지방법원)?\s*"
    r"(?P<year>\d{4})\s*(?P<code>[가-힣]{1,4})\s*(?P<num>\d+)\b"
)

# Abolished or fabricated court names (Section 5.1 #2)
FABRICATED_COURT_RE = re.compile(
    r"\b(?:서울민사지방법원|서울형사지방법원|한국연방법원|연방대법원|중앙고등법원|고등대법원|[가-힣]+민사지방법원|[가-힣]+형사지방법원)\b"
)

EVIDENCE_TAG_RE = re.compile(r"<evidence>(.*?)</evidence>", re.DOTALL)


def verify_legal_text(text: str, current_year: int = 2026, source_text: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    cited_statutes: list[str] = []
    cited_precedents: list[str] = []

    # 1. Statutory bounds check (flexible spacing & span deduplication)
    matched_spans: list[tuple[int, int]] = []
    sorted_statutes = sorted(STATUTE_BOUNDS.items(), key=lambda x: len(x[0]), reverse=True)

    for statute_name, max_art in sorted_statutes:
        pattern = _make_statute_pattern(statute_name)
        for match in pattern.finditer(text):
            span = match.span()
            if any(s <= span[0] and span[1] <= e for s, e in matched_spans):
                continue
            matched_spans.append(span)
            art_num = int(match.group(1))
            full_ref = match.group(0)
            cited_statutes.append(full_ref)
            if art_num < 1 or art_num > max_art:
                errors.append(
                    f"[{statute_name}] 허위 조문 날조: {full_ref} - "
                    f"현행 {statute_name}은 제1조~제{max_art}조까지만 존재합니다."
                )

    # 2. Precedent format and year sanity check
    for match in PRECEDENT_RE.finditer(text):
        year = int(match.group("year"))
        code = match.group("code")
        num = match.group("num")
        case_str = f"{year}{code}{num}"
        cited_precedents.append(case_str)

        if year > current_year:
            errors.append(
                f"[판례 날조] 미래 연도 판결 인용: {case_str} - "
                f"현재 연도({current_year}년)보다 미래의 사건번호는 날조된 환각입니다."
            )
        elif year < 1948:
            errors.append(
                f"[판례 날조] 대한민국 사법부 수립 이전 연도 판결: {case_str} (1948년 이전)."
            )

        if code not in VALID_CASE_CODES:
            warnings.append(
                f"[판례 부호 의심] 비표준 사건부호 인용: '{code}' in {case_str} - "
                f"대법원 규격 사건부호 여부를 확인하십시오."
            )

    # 3. Fabricated or abolished court names check (Section 5.1 #2)
    for m in FABRICATED_COURT_RE.finditer(text):
        fake_court = m.group(0)
        errors.append(
            f"[법원 명칭 날조] 폐지되거나 실존하지 않는 법원 명칭 인용: {fake_court} (Section 5.1 위반)"
        )

    # 4. Evidence tag attribution check (Section 3.2 #1)
    evidence_matches = EVIDENCE_TAG_RE.findall(text)
    for quote in evidence_matches:
        q_strip = quote.strip()
        if not q_strip:
            errors.append("<evidence> 태그가 비어 있습니다. 답변 근거 구절을 채우십시오.")
        elif source_text:
            # Check verbatim presence in source text
            clean_quote = re.sub(r"\s+", " ", q_strip)
            clean_source = re.sub(r"\s+", " ", source_text)
            if clean_quote not in clean_source:
                errors.append(
                    f"근거 인용 불일치: <evidence> 구절('{q_strip[:25]}...')이 원문(source)에 존재하지 않습니다."
                )

    # 5. Morphological grounding check if source text is provided (Section 5.2)
    if source_text:
        try:
            from scripts.korean_morph_grounding import calculate_grounding_overlap
        except ImportError:
            try:
                from korean_morph_grounding import calculate_grounding_overlap
            except ImportError:
                calculate_grounding_overlap = None

        if calculate_grounding_overlap is not None:
            overlap = calculate_grounding_overlap(source_text, text, threshold=0.65)
            if not overlap["is_grounded"]:
                warnings.append(
                    f"형태소 그라운딩 미달 ({overlap['grounding_score']*100:.1f}% < 65%): "
                    f"원문에 없는 고유/전문 용어 다수 사용 {overlap['unsupported_terms'][:5]}"
                )

    # 6. Grounding notice check for legal drafts
    if "# 소 장" in text or "# 준 비 서 면" in text or "# 고 소 장" in text:
        if "변호사" not in text and "AI 생성" not in text:
            warnings.append("법률 문서 초안에 필수 법적 고지(변호사 검토 안내)가 누락되었습니다.")

    verdict = "FAIL" if errors else ("WARN" if warnings else "PASS")
    return {
        "verdict": verdict,
        "errors": errors,
        "warnings": warnings,
        "cited_statutes": sorted(list(set(cited_statutes))),
        "cited_precedents": sorted(list(set(cited_precedents))),
    }


def verify_legal_file(file_path: str | Path, current_year: int = 2026, source_path: str | Path | None = None) -> dict:
    path = Path(file_path)
    if not path.is_file():
        return {
            "verdict": "FAIL",
            "errors": [f"File not found: {file_path}"],
            "warnings": [],
            "cited_statutes": [],
            "cited_precedents": [],
        }
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8-sig", errors="replace")

    source_text = None
    if source_path:
        sp = Path(source_path)
        if sp.is_file():
            source_text = sp.read_text(encoding="utf-8", errors="replace")

    return verify_legal_text(content, current_year=current_year, source_text=source_text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Korean Legal and Precedent Hallucination Verifier"
    )
    parser.add_argument("file", help="Path to legal document (.md, .txt) to verify")
    parser.add_argument("--source", help="Optional path to source evidence/facts for grounding check")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well")
    args = parser.parse_args(argv)

    result = verify_legal_file(args.file, source_path=args.source)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["errors"]:
            print(f"[FAIL] Legal hallucination detected ({len(result['errors'])} errors):", file=sys.stderr)
            for err in result["errors"]:
                print(f"  - ERROR: {err}", file=sys.stderr)
        if result["warnings"]:
            print(f"[WARN] Legal warnings ({len(result['warnings'])} warnings):", file=sys.stderr)
            for warn in result["warnings"]:
                print(f"  - WARN: {warn}", file=sys.stderr)
        if result["verdict"] == "PASS":
            print(f"[PASS] All {len(result['cited_statutes'])} statutes and {len(result['cited_precedents'])} precedents grounded.")

    if result["errors"] or (args.strict and result["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
