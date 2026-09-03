#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""korean_morph_grounding.py — Korean Morphological Hybrid Grounding & Term Extraction.

Implements Section 5.2 of gemini_hallucination_mitigation_deep_dive.md.
Leverages Kiwi (kiwipiepy) morphological analysis to:
1. Extract content morphemes (NNG, NNP, NR, SL, SH, SN) while stripping case particles
   (조사: 은/는/이/가/을/를/의/에/에서/로/으로) and endings (어미), eliminating agglutinative
   mismatch that causes LLMs to fabricate or miss legal/statutory terms.
2. Register specialized Korean legal terminology into the Kiwi dictionary (e.g., 갑호증,
   을호증, 청구취지, 요건사실, 부당이득, 소송비용, 지연손해금).
3. Compute lexical/semantic grounding overlap between source evidence and generated legal
   drafts or summaries, flagging unsupported or hallucinated technical terms.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Optional Kiwi import with graceful regex fallback
try:
    from kiwipiepy import Kiwi
    _HAS_KIWI = True
except ImportError:
    Kiwi = None
    _HAS_KIWI = False

# Legal domain terms to register into Kiwi user dictionary
LEGAL_DOMAIN_TERMS = [
    ("갑호증", "NNP"),
    ("을호증", "NNP"),
    ("병호증", "NNP"),
    ("서증명", "NNG"),
    ("입증방법", "NNG"),
    ("소장", "NNG"),
    ("준비서면", "NNG"),
    ("답변서", "NNG"),
    ("고소장", "NNG"),
    ("내용증명", "NNG"),
    ("청구취지", "NNG"),
    ("청구원인", "NNG"),
    ("요건사실", "NNG"),
    ("지연손해금", "NNG"),
    ("소송비용", "NNG"),
    ("가집행", "NNG"),
    ("부당이득", "NNG"),
    ("불법행위", "NNG"),
    ("채무불이행", "NNG"),
    ("손해배상", "NNG"),
    ("대여금", "NNG"),
    ("차용증", "NNG"),
    ("상계항변", "NNG"),
    ("동시이행", "NNG"),
    ("소멸시효", "NNG"),
    ("변론종결", "NNG"),
    ("석명권", "NNG"),
    ("기판력", "NNG"),
    ("개인정보보호법", "NNP"),
    ("정보통신망법", "NNP"),
    ("부정경쟁방지법", "NNP"),
    ("특정금융정보법", "NNP"),
    ("전자문서법", "NNP"),
    ("전자상거래법", "NNP"),
    ("자본시장법", "NNP"),
    ("신용정보법", "NNP"),
]

# Morphological tags considered meaningful content terms
CONTENT_TAGS = {"NNG", "NNP", "NR", "SL", "SH", "SN"}

_KIWI_INSTANCE = None


def get_kiwi_instance():
    global _KIWI_INSTANCE
    if not _HAS_KIWI:
        return None
    if _KIWI_INSTANCE is None:
        try:
            k = Kiwi()
            for word, tag in LEGAL_DOMAIN_TERMS:
                try:
                    k.add_user_word(word, tag)
                except Exception:
                    pass
            _KIWI_INSTANCE = k
        except Exception:
            _KIWI_INSTANCE = None
    return _KIWI_INSTANCE


def extract_content_morphemes(text: str, min_len: int = 2) -> list[str]:
    """Extracts base Korean nouns and content terms, stripping particles and endings."""
    if not text:
        return []

    kiwi = get_kiwi_instance()
    if kiwi is not None:
        try:
            tokens = kiwi.tokenize(text)
            results = []
            for t in tokens:
                if t.tag in CONTENT_TAGS and len(t.form) >= min_len:
                    results.append(t.form)
            return results
        except Exception:
            pass

    # Graceful fallback: regex-based noun extraction stripping common Korean particles
    particles = r"(?:은|는|이|가|을|를|의|에|에서|로|으로|와|과|도|만|에게|한테|이나|나|으로서|으로써)$"
    words = re.findall(r"[가-힣a-zA-Z0-9]+", text)
    fallback_tokens = []
    for w in words:
        stripped = re.sub(particles, "", w)
        if len(stripped) >= min_len:
            fallback_tokens.append(stripped)
    return fallback_tokens


VALID_CASE_CODES = {
    "가단", "가합", "가소", "나", "다", "라", "마", "그", "바", "자", "차",
    "카", "카단", "카합", "카기", "카담", "카조", "카열", "카경",
    "고단", "고합", "고약", "노", "도", "로", "모", "오", "보", "코",
    "드", "드단", "드합", "르", "르단", "르합", "므", "스", "으",
    "느", "느단", "느합", "즈", "즈단", "즈합",
    "회단", "회합", "회개", "개회", "개단", "개합", "하단", "하합", "하면", "개확",
    "구", "구합", "구단", "누", "두", "루", "무", "허",
    "헌가", "헌나", "헌다", "헌라", "헌마", "헌바", "헌사", "헌아",
    "푸", "버",
    "재가단", "재가합", "재다", "재나", "재도", "재노", "재고단", "재고합",
}


def extract_legal_entities(text: str) -> dict[str, list[str]]:
    """Extracts formal legal statutes, case codes, evidence labels, and key entities."""
    statute_re = re.compile(
        r"([가-힣]{2,20}(?:법률|법)?)\s*제\s*(\d+)\s*조(?:\s*의\s*(\d+))?"
    )
    precedent_re = re.compile(
        r"\b(?:대법원|서울고등법원|헌법재판소|[가-힣]{2,6}고등법원|[가-힣]{2,6}지방법원)?\s*(\d{4})\s*([가-힣]{1,4})\s*(\d+)\b"
    )
    evidence_re = re.compile(r"((?:갑|을|병)\s*제\s*\d+\s*호증(?:\s*의\s*\d+)?)")

    statutes = [m.group(0) for m in statute_re.finditer(text)]
    precedents = [
        f"{m.group(1)}{m.group(2)}{m.group(3)}"
        for m in precedent_re.finditer(text)
        if m.group(2) in VALID_CASE_CODES
    ]
    evidences = [m.group(1) for m in evidence_re.finditer(text)]

    # Morphological content nouns
    morphemes = extract_content_morphemes(text)

    return {
        "statutes": sorted(list(set(statutes))),
        "precedents": sorted(list(set(precedents))),
        "evidence_labels": sorted(list(set(evidences))),
        "content_morphemes": sorted(list(set(morphemes))),
    }


def calculate_grounding_overlap(
    source_text: str,
    target_text: str,
    threshold: float = 0.70,
) -> dict[str, Any]:
    """Calculates morphological grounding overlap between source evidence and target text.

    Args:
        source_text: Ground truth evidence, input facts, or statutory text.
        target_text: Generated legal draft, summary, or argument.
        threshold: Minimum grounding ratio (0.0 to 1.0) to pass.

    Returns:
        dict with overlap metrics, unsupported terms, and pass/fail verdict.
    """
    source_terms = set(extract_content_morphemes(source_text))
    target_terms = set(extract_content_morphemes(target_text))

    if not target_terms:
        return {
            "grounding_score": 1.0,
            "is_grounded": True,
            "overlap_count": 0,
            "target_term_count": 0,
            "source_term_count": len(source_terms),
            "unsupported_terms": [],
        }

    supported_terms = target_terms.intersection(source_terms)
    unsupported_terms = sorted(list(target_terms - source_terms))
    score = len(supported_terms) / len(target_terms)

    return {
        "grounding_score": round(score, 3),
        "is_grounded": score >= threshold,
        "overlap_count": len(supported_terms),
        "target_term_count": len(target_terms),
        "source_term_count": len(source_terms),
        "supported_terms": sorted(list(supported_terms)),
        "unsupported_terms": unsupported_terms,
        "has_kiwi": _HAS_KIWI,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Korean Morphological Hybrid Grounding & Term Extraction (Kiwi)"
    )
    parser.add_argument("--source", help="Source evidence / fact file (.txt, .md, .json)")
    parser.add_argument("--target", help="Target generated draft / claim file (.txt, .md)")
    parser.add_argument("--text", help="Direct Korean text string to analyze")
    parser.add_argument("--threshold", type=float, default=0.70, help="Minimum grounding threshold")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args(argv)

    if args.text:
        entities = extract_legal_entities(args.text)
        if args.json:
            print(json.dumps(entities, ensure_ascii=False, indent=2))
        else:
            print(f"[Entities] Statutes: {entities['statutes']}")
            print(f"[Entities] Precedents: {entities['precedents']}")
            print(f"[Entities] Evidence: {entities['evidence_labels']}")
            print(f"[Morphemes] Sample ({len(entities['content_morphemes'])}): {entities['content_morphemes'][:15]}")
        return 0

    if args.source and args.target:
        source_path = Path(args.source)
        target_path = Path(args.target)
        if not source_path.is_file():
            print(f"Error: Source file not found: {source_path}", file=sys.stderr)
            return 2
        if not target_path.is_file():
            print(f"Error: Target file not found: {target_path}", file=sys.stderr)
            return 2

        src_text = source_path.read_text(encoding="utf-8", errors="replace")
        tgt_text = target_path.read_text(encoding="utf-8", errors="replace")

        result = calculate_grounding_overlap(src_text, tgt_text, threshold=args.threshold)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            verdict = "PASS" if result["is_grounded"] else "FAIL"
            print(f"[{verdict}] Morphological Grounding Score: {result['grounding_score'] * 100:.1f}% (Threshold: {args.threshold * 100:.0f}%)")
            print(f"  - Supported Terms: {result['overlap_count']} / {result['target_term_count']}")
            if result["unsupported_terms"]:
                print(f"  - Unsupported Novel Terms ({len(result['unsupported_terms'])}): {result['unsupported_terms'][:10]}")
        return 0 if result["is_grounded"] else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
