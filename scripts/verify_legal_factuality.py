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

# Standard Korean particle/suffix lookahead for court and agency bounds
KOREAN_PARTICLE_SUFFIX = (
    r"(?:장관|차관|처장|청장|국장|위원장|부장|판사|검사|법원장|령|고시|지침|규정)?"
    r"(?:[이가은는을를의에]|에서|에게|서|과|와|도|만|부터|까지|로|으로|란|이란|라|라는|이라|이라는|며|이며|고|이고|통해|대해|관해)?"
    r"(?![가-힣])"
)

# Abolished or fabricated court names (Section 5.1 #2)
FABRICATED_COURT_RE = re.compile(
    rf"(?<![가-힣])(?P<court>서울민사지방법원|서울형사지방법원|한국연방법원|연방대법원|중앙고등법원|고등대법원|[가-힣]+민사지방법원|[가-힣]+형사지방법원){KOREAN_PARTICLE_SUFFIX}"
)

# Fabricated government agencies and investigative bodies (Section 5.1 #2)
FABRICATED_AGENCY_RE = re.compile(
    rf"(?<![가-힣])(?P<agency>디지털포렌식청|사이버수사처|국가포렌식연구원|사이버범죄특별수사처|경찰청사이버보안국|사이버보안청|인공지능윤리청|국가데이터청|개인정보보호청|사이버테러수사본부|정보보호조사위원회|디지털윤리위원회|한국연방검찰청|대검찰청사이버수사청){KOREAN_PARTICLE_SUFFIX}"
)

# Abolished / obsolete government ministries and their current successors (Section 5.1 #2)
ABOLISHED_GOV_AGENCIES: dict[str, tuple[str, str]] = {
    "정보통신부": ("2008년 폐지", "과학기술정보통신부 또는 방송통신위원회"),
    "문화공보부": ("1990년 폐지", "문화체육관광부"),
    "재정경제원": ("1998년 폐지", "기획재정부"),
    "재정경제부": ("2008년 개편", "기획재정부"),
    "미래창조과학부": ("2017년 개편", "과학기술정보통신부"),
    "과학기술처": ("1998년 개편", "과학기술정보통신부"),
    "과학기술부": ("2008년 개편", "과학기술정보통신부"),
    "교육인적자원부": ("2008년 개편", "교육부"),
    "교육과학기술부": ("2013년 개편", "교육부"),
    "건설교통부": ("2008년 개편", "국토교통부"),
    "국토해양부": ("2013년 개편", "국토교통부"),
    "행정자치부": ("2017년 개편", "행정안전부"),
    "안전행정부": ("2014년 개편", "행정안전부"),
    "국민안전처": ("2017년 개편", "행정안전부/소방청/해양경찰청"),
    "산업자원부": ("2008년 개편", "산업통상자원부"),
    "지식경제부": ("2013년 개편", "산업통상자원부"),
    "상공자원부": ("1994년 개편", "산업통상자원부"),
    "동력자원부": ("1993년 개편", "산업통상자원부"),
    "보건사회부": ("1994년 개편", "보건복지부"),
    "노동부": ("2010년 개편", "고용노동부"),
    "총무처": ("1998년 폐지", "행정안전부"),
    "내무부": ("1998년 폐지", "행정안전부"),
    "공보처": ("1998년 폐지", "문화체육관광부"),
    "기획예산처": ("2008년 개편", "기획재정부"),
    "철도청": ("2005년 개편", "한국철도공사/국가철도공단"),
}

EVIDENCE_TAG_RE = re.compile(r"<evidence(?:\s+[^>]*)?>(.*?)</evidence>", re.DOTALL | re.IGNORECASE)


def verify_legal_text(
    text: str,
    current_year: int = 2026,
    source_text: str | None = None,
    morph_grounding: bool = False,
    high_fidelity: bool = False,
    allow_historical: bool = False,
    claim_ledger_path: str | Path | None = None,
) -> dict:
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

    # 3-1. Fabricated or abolished court names check (Section 5.1 #2)
    for m in FABRICATED_COURT_RE.finditer(text):
        fake_court = m.group("court")
        errors.append(
            f"[법원 명칭 날조] 폐지되거나 실존하지 않는 법원 명칭 인용: {fake_court} (Section 5.1 위반)"
        )

    # 3-2. Fabricated government agencies and committees (Section 5.1 #2)
    for m in FABRICATED_AGENCY_RE.finditer(text):
        fake_agency = m.group("agency")
        errors.append(
            f"[정부기관 명칭 날조] 실존하지 않는 가짜 관공서/기구 명칭 인용: {fake_agency} (Section 5.1 위반)"
        )

    # 3-3. Abolished government ministries check (Section 5.1 #2)
    for agency, (abolish_info, successor) in ABOLISHED_GOV_AGENCIES.items():
        pat = re.compile(rf"(?<![가-힣]){re.escape(agency)}{KOREAN_PARTICLE_SUFFIX}")
        if pat.search(text):
            successor_candidates = [s.strip() for s in re.split(r"또는|/|,", successor) if s.strip()]
            has_successor_annotation = any(cand in text for cand in successor_candidates)
            has_historical_marker = bool(
                re.search(rf"\((?:구|과거)\s*{re.escape(agency)}\)", text)
                or re.search(rf"{re.escape(agency)}\s*\((?:현|현행)", text)
            )

            if has_successor_annotation or has_historical_marker or allow_historical:
                warnings.append(
                    f"[정부기관 역사적 명칭 인용] 폐지된 구 정부 부처명 인용: '{agency}' ({abolish_info}, 현행 '{successor}' 병기됨/역사적 검토 허용)"
                )
            else:
                errors.append(
                    f"[정부기관 명칭 오류/날조] 폐지된 구 정부 부처명 인용: '{agency}' ({abolish_info}, 현행 '{successor}' 명칭 사용 필수) (Section 5.1 위반)"
                )

    # 3-4. Optional Claim Ledger integration (Section 6)
    if claim_ledger_path:
        try:
            from scripts.verify_claim_ledger import verify_claim_ledger_file
        except ImportError:
            try:
                from verify_claim_ledger import verify_claim_ledger_file
            except ImportError:
                verify_claim_ledger_file = None

        if verify_claim_ledger_file is not None:
            ledger_report = verify_claim_ledger_file(claim_ledger_path, synthesis_path=None)
            # Check cited claims in text
            citation_re = re.compile(r"\[Claim\s*([A-Za-z0-9._-]+)\]", re.IGNORECASE)
            for m in citation_re.finditer(text):
                cited_id = f"Claim {m.group(1)}"
                found = next((r for r in ledger_report["rows"] if r["claimId"].lower() == cited_id.lower()), None)
                if not found:
                    errors.append(f"[Claim Ledger 위반] 문서에 인용된 [{cited_id}]가 claim-ledger.md에 등록되어 있지 않습니다.")
                elif found["status"] != "VERIFIED":
                    errors.append(
                        f"[Claim Ledger 위반] 문서에 인용된 [{cited_id}]의 원장 상태가 '{found['status']}'입니다. "
                        "오직 VERIFIED 주장만 최종 문서 인용이 허용됩니다 (Section 6 위반)."
                    )
            if not ledger_report["ok"]:
                for v in ledger_report["violations"]:
                    errors.append(f"[Claim Ledger 위반] [{v['claimId']}] {v['violation']}")
        else:
            warnings.append("verify_claim_ledger 모듈을 찾을 수 없어 원장 검증을 건너뛰었습니다.")

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
        else:
            warnings.append(
                f"<evidence> 인용 구절('{q_strip[:25]}...')이 존재하나 대조할 원문(--source)이 지정되지 않았습니다."
            )

    # 5. High-Fidelity non-parametric gate (Section 4.2)
    if high_fidelity:
        if not source_text:
            errors.append("[High-Fidelity Grounding 위반] High-Fidelity 검증을 위한 원문(--source)이 지정되지 않았습니다.")
        elif not evidence_matches:
            errors.append("[High-Fidelity Grounding 위반] 사실관계 주장을 뒷받침하는 <evidence> 원문 인용 태그가 없습니다.")

    # 6. Morphological grounding check if source text is provided (Section 5.2)
    if source_text and (morph_grounding or high_fidelity):
        try:
            from scripts.korean_morph_grounding import calculate_grounding_overlap
        except ImportError:
            try:
                from korean_morph_grounding import calculate_grounding_overlap
            except ImportError:
                calculate_grounding_overlap = None

        if calculate_grounding_overlap is not None:
            # If target text has dedicated factual sections, isolate them to avoid boilerplate dilution
            fact_section_match = re.search(
                r"(?:^|\n)\s*(?:#{1,4}\s*|\d+[\.\)]\s*|제\s*\d+\s*조?\s*|\b|【|\[)?\s*(?:\d+[\.\)]\s*)?"
                r"(?:청구원인|주장 및 항변|범죄사실|사실관계|사실\s*관계|통고 내용|통고\s*내용|신청이유|주장의 요지)\b[^\n]*\n?"
                r"(.*?)"
                r"(?=\n#{1,2}\s|\n\s*(?:#{1,4}\s*|\d+[\.\)]\s*|제\s*\d+\s*조?\s*|【|\[)?\s*(?:\d+[\.\)]\s*)?(?:법적|법률|입증|증거|결론|첨부|신청|관할|판단|이유|고소|주문)|\Z)",
                text,
                re.DOTALL,
            )
            eval_target = fact_section_match.group(1) if fact_section_match else text
            clean_tgt = re.sub(r"<[^>]+>", " ", eval_target)
            thresh = 0.65
            overlap = calculate_grounding_overlap(source_text, clean_tgt, threshold=thresh, filter_procedural=True)
            if not overlap["is_grounded"]:
                msg = (
                    f"형태소 그라운딩 미달 ({overlap['grounding_score']*100:.1f}% < {int(thresh*100)}%): "
                    f"원문에 없는 고유/전문 용어 다수 사용 {overlap['unsupported_terms'][:5]}"
                )
                if high_fidelity:
                    errors.append(f"[High-Fidelity Grounding 위반] {msg}")
                else:
                    warnings.append(msg)

    # 7. Grounding notice check for legal drafts
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


def verify_legal_file(
    file_path: str | Path,
    current_year: int = 2026,
    source_path: str | Path | None = None,
    morph_grounding: bool = False,
    high_fidelity: bool = False,
    allow_historical: bool = False,
    claim_ledger_path: str | Path | None = None,
) -> dict:
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

    result = verify_legal_text(
        content,
        current_year=current_year,
        source_text=source_text,
        morph_grounding=morph_grounding,
        high_fidelity=high_fidelity,
        allow_historical=allow_historical,
    )

    # Section 6 Claim Ledger integration
    if claim_ledger_path:
        try:
            from scripts.verify_claim_ledger import verify_claim_ledger_file
        except ImportError:
            try:
                from verify_claim_ledger import verify_claim_ledger_file
            except ImportError:
                verify_claim_ledger_file = None

        if verify_claim_ledger_file is not None:
            ledger_report = verify_claim_ledger_file(claim_ledger_path, synthesis_path=file_path)
            if not ledger_report["ok"]:
                for v in ledger_report["violations"]:
                    result["errors"].append(f"[Claim Ledger 위반] [{v['claimId']}] {v['violation']}")
            result["claim_ledger"] = {
                "ok": ledger_report["ok"],
                "totalClaims": ledger_report["totalClaims"],
                "verifiedCount": ledger_report["verifiedCount"],
            }
        else:
            result["warnings"].append("verify_claim_ledger 모듈을 찾을 수 없어 원장 검증을 건너뛰었습니다.")

    if result["errors"]:
        result["verdict"] = "FAIL"
    elif result["warnings"] and result["verdict"] == "PASS":
        result["verdict"] = "WARN"

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Korean Legal and Precedent Hallucination Verifier"
    )
    parser.add_argument("file", help="Path to legal document (.md, .txt) to verify")
    parser.add_argument("--source", help="Optional path to source evidence/facts for grounding check")
    parser.add_argument("--claim-ledger", help="Optional path to claim-ledger.md for Section 6 verification")
    parser.add_argument("--allow-historical", action="store_true", help="Allow historical abolished ministry citations (warning instead of fatal error)")
    parser.add_argument("--morph-grounding", action="store_true", help="Enforce Kiwi morphological hybrid grounding check against source")
    parser.add_argument("--high-fidelity", action="store_true", help="Enforce Vertex AI High-Fidelity strict non-parametric grounding mode")
    parser.add_argument("--json", action="store_true", help="Output JSON results")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well")
    args = parser.parse_args(argv)

    result = verify_legal_file(
        args.file,
        source_path=args.source,
        morph_grounding=args.morph_grounding,
        high_fidelity=args.high_fidelity,
        allow_historical=args.allow_historical,
        claim_ledger_path=args.claim_ledger,
    )

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
