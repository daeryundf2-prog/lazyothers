#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stamp_evidence.py - 대법원 전자소송(ECFS) 규격 서증(갑/을 제O호증) 표찰 및 Bates 번호 스탬핑 도구
"""

import os
import sys
import argparse

def stamp_pdf_pymupdf(input_pdf: str, output_pdf: str, label: str, bates_prefix: str = "P", start_page: int = 1):
    """PyMuPDF(fitz)를 활용한 고품질 서증 라벨 및 Bates 번호 인자"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("[!] PyMuPDF(fitz)가 설치되어 있지 않습니다. pip install pymupdf 를 실행하십시오.", file=sys.stderr)
        return False

    doc = fitz.open(input_pdf)
    total_pages = len(doc)
    
    print(f"[*] Processing {total_pages} pages in '{input_pdf}'...")
    
    for idx, page in enumerate(doc):
        current_page_num = start_page + idx
        rect = page.rect
        
        # 1. 서증 표찰 (첫 페이지 우측 상단 또는 전 페이지)
        if idx == 0 or True:  # 전자소송 실무: 전 페이지 또는 첫 페이지 상단에 표찰 박스
            # 표찰 박스 좌표 (우측 상단 마진 20pt)
            box_width = 110
            box_height = 24
            box_x1 = rect.width - 25 - box_width
            box_y1 = 20
            box_x2 = rect.width - 25
            box_y2 = box_y1 + box_height
            
            # 외곽선 사각형 드로잉 (빨간색/검정색 테두리)
            page.draw_rect(fitz.Rect(box_x1, box_y1, box_x2, box_y2), color=(0.8, 0, 0), width=1.5, fill=(1, 1, 1))
            
            # 서증 텍스트 삽입 (예: "갑 제 1 호증", "을 제 2 호증의 1")
            text_rect = fitz.Rect(box_x1, box_y1 + 4, box_x2, box_y2)
            page.insert_textbox(
                text_rect,
                label,
                fontsize=11,
                fontname="helv",  # 한글 폰트 지원 시 지정
                color=(0.8, 0, 0),
                align=fitz.TEXT_ALIGN_CENTER
            )
            
        # 2. Bates 일련번호 (하단 중앙 또는 우측 하단)
        bates_text = f"{bates_prefix}-{current_page_num:04d} / {bates_prefix}-{start_page + total_pages - 1:04d}"
        bates_rect = fitz.Rect(rect.width / 2 - 80, rect.height - 25, rect.width / 2 + 80, rect.height - 10)
        page.insert_textbox(
            bates_rect,
            bates_text,
            fontsize=9,
            fontname="helv",
            color=(0.2, 0.2, 0.2),
            align=fitz.TEXT_ALIGN_CENTER
        )

    # PDF/A 최적화 및 저장
    doc.save(output_pdf, garbage=4, deflate=True)
    doc.close()
    print(f"[OK] Successfully generated court-stamped PDF: {output_pdf}")
    return True

def main():
    parser = argparse.ArgumentParser(description="대법원 전자소송 서증 표찰(갑/을 제O호증) 및 Bates 번호 스탬퍼")
    parser.add_argument("input_pdf", help="원본 PDF 파일 경로")
    parser.add_argument("--output", "-o", required=True, help="스탬핑 완료된 출력 PDF 경로")
    parser.add_argument("--label", "-l", required=True, help="서증 부호 및 번호 (예: '갑 제1호증', '을 제2호증의 1')")
    parser.add_argument("--prefix", "-p", default="P", help="Bates 페이지 접두사 (기본: 'P')")
    parser.add_argument("--start", "-s", type=int, default=1, help="시작 페이지 번호 (기본: 1)")

    args = parser.parse_args()
    
    if not os.path.exists(args.input_pdf):
        print(f"Error: Input file not found: {args.input_pdf}", file=sys.stderr)
        sys.exit(1)
        
    success = stamp_pdf_pymupdf(
        input_pdf=args.input_pdf,
        output_pdf=args.output,
        label=args.label,
        bates_prefix=args.prefix,
        start_page=args.start
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
