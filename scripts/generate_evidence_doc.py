#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_evidence_doc.py - 대법원 제출용 증거설명서(Evidence Explanation Document) 자동 생성기
"""

import os
import sys
import json
import argparse
import hashlib
from datetime import datetime


def calculate_sha256(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "N/A"
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def _escape_cell(text: str) -> str:
    """Escape markdown table breaking characters."""
    if text is None:
        return ""
    return str(text).replace("|", "\\|").replace("\n", " ").replace("\r", "")


def resolve_evidence_hashes(evidence_list: list, base_dir: str = ""):
    """sha256이 없는 항목에 대해 파일 해시를 계산해 채운다.

    상대 경로는 --input-json 파일이 있는 디렉토리 기준으로 해석한다.
    """
    for item in evidence_list:
        if item.get("sha256"):
            continue
        file_path = item.get("file_path", "")
        if not file_path:
            item["sha256"] = "N/A"
            continue
        candidates = [file_path]
        if base_dir and not os.path.isabs(file_path):
            candidates.insert(0, os.path.join(base_dir, file_path))
        for cand in candidates:
            if os.path.exists(cand):
                item["sha256"] = calculate_sha256(cand)
                break
        else:
            item["sha256"] = "N/A (file not found)"


def generate_evidence_markdown(case_info: dict, evidence_list: list, output_path: str):
    """표준 증거설명서 마크다운 생성"""
    lines = []
    lines.append("# 증 거 설 명 서\n")
    lines.append(f"**사 건:** {_escape_cell(case_info.get('case_number', '202X가합XXXX호'))} {_escape_cell(case_info.get('case_name', '손해배상(기) 등'))}")
    lines.append(f"**원 고:** {_escape_cell(case_info.get('plaintiff', '홍길동'))}")
    lines.append(f"**피 고:** {_escape_cell(case_info.get('defendant', '주식회사 XXX'))}\n")
    lines.append("위 사건에 관하여 원고(또는 피고)는 주장사실을 입증하기 위하여 다음과 같이 증거를 제출합니다.\n")
    lines.append("### 다 음\n")
    lines.append("| 순번 | 서증부호 및 번호 | 서증명 (파일명) | 작성자 / 일자 | 입증취지 (Proof Purpose) | 비고 (포렌식 무결성 SHA-256) |")
    lines.append("| :---: | :--- | :--- | :---: | :--- | :--- |")

    for idx, item in enumerate(evidence_list, 1):
        label = _escape_cell(item.get("label", f"갑 제{idx}호증"))
        title = _escape_cell(item.get("title", f"증거물_{idx}"))
        author_date = _escape_cell(f"{item.get('author', '작성자불상')} / {item.get('date', datetime.now().strftime('%Y-%m-%d'))}")
        purpose = _escape_cell(item.get("purpose", "주장사실 입증"))
        file_hash = _escape_cell(item.get("sha256", "N/A"))

        lines.append(f"| {idx} | **{label}** | {title} | {author_date} | {purpose} | `{file_hash}` |")

    lines.append("\n### 첨 부 서 류\n")
    for idx, item in enumerate(evidence_list, 1):
        lines.append(f"1. {_escape_cell(item.get('label', f'갑 제{idx}호증'))} 각 1통")

    lines.append(f"\n**작성일자:** {datetime.now().strftime('%Y년 %m월 %d일')}")
    lines.append(f"**제출인:** {_escape_cell(case_info.get('submitter', '원고 소송대리인'))}")
    lines.append(f"**{_escape_cell(case_info.get('court', '서울중앙지방법원'))} 귀중**\n")

    content = "\n".join(lines)
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[OK] Successfully generated Evidence Statement: {output_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="대법원 표준 규격 증거설명서 자동 생성기")
    parser.add_argument("--input-json", "-i", help="증거 목록 JSON 파일 경로")
    parser.add_argument("--output", "-o", default="증거설명서.md", help="출력 파일 경로 (.md)")
    parser.add_argument("--case-num", default="202X가합XXXX호", help="사건번호")
    parser.add_argument("--case-name", default="영업비밀침해금지 등 청구의 소", help="사건명")
    parser.add_argument("--court", default="서울중앙지방법원", help="관할 법원")

    args = parser.parse_args(argv)

    evidence_list = []
    case_info = {
        "case_number": args.case_num,
        "case_name": args.case_name,
        "court": args.court,
        "plaintiff": "원고",
        "defendant": "피고",
        "submitter": "소송대리인"
    }

    if args.input_json:
        if not os.path.exists(args.input_json):
            print(f"[WARN] input JSON not found: {args.input_json}", file=sys.stderr)
            print("[WARN] Using built-in sample data — replace before court submission!", file=sys.stderr)
            evidence_list = []
        else:
            with open(args.input_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    case_info.update(data.get("case_info", {}))
                    evidence_list = data.get("evidence_list", [])
                elif isinstance(data, list):
                    evidence_list = data
                else:
                    print(f"[WARN] Unexpected JSON root type: {type(data)}", file=sys.stderr)

    # 상대 경로는 input-json 위치 기준으로 해석해 전체 SHA-256을 채운다
    base_dir = os.path.dirname(os.path.abspath(args.input_json)) if args.input_json else ""
    resolve_evidence_hashes(evidence_list, base_dir)

    if not evidence_list:
        if args.input_json:
            print("[WARN] evidence_list is empty — generating sample placeholder. DO NOT submit as-is.", file=sys.stderr)
        else:
            print("[WARN] --input-json not provided — generating sample placeholder. Provide real evidence JSON before submission.", file=sys.stderr)
        evidence_list = [
            {
                "label": "갑 제1호증의 1",
                "title": "[SAMPLE] 피고-원고 카카오톡 대화 내역 캡처본 — 실제 증거로 교체 필요",
                "author": "원고",
                "date": "2024-01-16",
                "purpose": "피고가 원고에게 영업비밀 유출을 제안한 사실 입증"
            },
            {
                "label": "갑 제1호증의 2",
                "title": "[SAMPLE] USB 저장매체 파일 반출 타임스탬프 분석서 — 실제 증거로 교체 필요",
                "author": "포렌식 감정관",
                "date": "2024-01-17",
                "purpose": "피고 컴퓨터에서 업무시간 외 대용량 소스코드가 외장 USB로 복사된 사실 입증"
            }
        ]

    generate_evidence_markdown(case_info, evidence_list, args.output)


if __name__ == "__main__":
    main()
