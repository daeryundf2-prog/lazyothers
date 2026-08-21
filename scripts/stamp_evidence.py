#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stamp_evidence.py - 대법원 전자소송(ECFS) 규격 서증(갑/을 제O호증) 표찰 및 Bates 번호 스탬핑 도구
"""

import os
import sys
import argparse


def _get_korean_font(page):
    """Try to use a Korean-capable font; fall back to helv."""
    # PyMuPDF built-in fonts: helv, cour, times etc have no Hangul glyphs.
    # If user placed a TTF (e.g., NotoSansKR) alongside, try to use it.
    # Otherwise, helv will render label as boxes — warn user.
    try:
        import fitz
        # Check if a Korean font file exists next to script
        for candidate in [
            os.path.join(os.path.dirname(__file__), "NotoSansKR-Regular.ttf"),
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        ]:
            if os.path.exists(candidate):
                # Register font for this page's document — use file-based font
                return candidate
    except Exception:
        pass
    return None


def stamp_pdf_pymupdf(input_pdf: str, output_pdf: str, label: str, bates_prefix: str = "P", start_page: int = 1, all_pages: bool = True):
    """PyMuPDF(fitz)를 활용한 고품질 서증 라벨 및 Bates 번호 인자"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("[!] PyMuPDF(fitz)가 설치되어 있지 않습니다. pip install pymupdf 를 실행하십시오.", file=sys.stderr)
        return False

    # Ensure output directory exists
    out_dir = os.path.dirname(os.path.abspath(output_pdf))
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    try:
        doc = fitz.open(input_pdf)
    except Exception as e:
        print(f"[!] Failed to open PDF: {e}", file=sys.stderr)
        return False

    if doc.is_encrypted:
        print("[!] Encrypted PDF requires password — cannot stamp", file=sys.stderr)
        doc.close()
        return False

    total_pages = len(doc)
    if total_pages == 0:
        print("[!] PDF has no pages", file=sys.stderr)
        doc.close()
        return False

    print(f"[*] Processing {total_pages} pages in '{input_pdf}'...")

    korean_font_path = _get_korean_font(doc[0]) if len(doc) > 0 else None
    if korean_font_path:
        print(f"[*] Using Korean font: {korean_font_path}")
    else:
        print("[WARN] No Korean TTF found — Hangul in label may render as boxes. Place NotoSansKR-Regular.ttf next to script.", file=sys.stderr)

    for idx, page in enumerate(doc):
        current_page_num = start_page + idx
        rect = page.rect

        # 1. 서증 표찰 — all_pages=True면 전 페이지, False면 첫 페이지만
        should_stamp = all_pages or idx == 0
        if should_stamp:
            box_width = 110
            box_height = 24
            box_x1 = rect.width - 25 - box_width
            box_y1 = 20
            box_x2 = rect.width - 25
            box_y2 = box_y1 + box_height

            page.draw_rect(fitz.Rect(box_x1, box_y1, box_x2, box_y2), color=(0.8, 0, 0), width=1.5, fill=(1, 1, 1))

            text_rect = fitz.Rect(box_x1, box_y1 + 4, box_x2, box_y2)
            # Use Korean font if available
            if korean_font_path:
                # Insert with file-based font
                try:
                    page.insert_textbox(
                        text_rect,
                        label,
                        fontsize=11,
                        fontfile=korean_font_path,
                        color=(0.8, 0, 0),
                        align=fitz.TEXT_ALIGN_CENTER,
                    )
                except Exception:
                    page.insert_textbox(
                        text_rect, label, fontsize=11, fontname="helv", color=(0.8, 0, 0), align=fitz.TEXT_ALIGN_CENTER
                    )
            else:
                page.insert_textbox(
                    text_rect,
                    label,
                    fontsize=11,
                    fontname="helv",
                    color=(0.8, 0, 0),
                    align=fitz.TEXT_ALIGN_CENTER,
                )

        # 2. Bates 일련번호 — 단일 번호 (예: P-0001)
        bates_text = f"{bates_prefix}-{current_page_num:04d}"
        bates_rect = fitz.Rect(rect.width / 2 - 80, rect.height - 25, rect.width / 2 + 80, rect.height - 10)
        page.insert_textbox(
            bates_rect,
            bates_text,
            fontsize=9,
            fontname="helv",
            color=(0.2, 0.2, 0.2),
            align=fitz.TEXT_ALIGN_CENTER,
        )

    try:
        doc.save(output_pdf, garbage=4, deflate=True)
    except Exception as e:
        print(f"[!] Failed to save PDF: {e}", file=sys.stderr)
        doc.close()
        return False
    doc.close()
    print(f"[OK] Successfully generated court-stamped PDF: {output_pdf} ({total_pages} pages, Bates {bates_prefix}-{start_page:04d}~{bates_prefix}-{start_page+total_pages-1:04d})")
    return True


def main():
    parser = argparse.ArgumentParser(description="대법원 전자소송 서증 표찰(갑/을 제O호증) 및 Bates 번호 스탬퍼")
    parser.add_argument("input_pdf", help="원본 PDF 파일 경로")
    parser.add_argument("--output", "-o", required=True, help="스탬핑 완료된 출력 PDF 경로")
    parser.add_argument("--label", "-l", required=True, help="서증 부호 및 번호 (예: '갑 제1호증', '을 제2호증의 1')")
    parser.add_argument("--prefix", "-p", default="P", help="Bates 페이지 접두사 (기본: 'P')")
    parser.add_argument("--start", "-s", type=int, default=1, help="시작 페이지 번호 (기본: 1)")
    parser.add_argument("--all-pages", action="store_true", default=True, help="전 페이지에 표찰 (기본: True)")
    parser.add_argument("--first-only", action="store_true", help="첫 페이지만 표찰 (지정시 --all-pages 무시)")

    args = parser.parse_args()

    if not os.path.exists(args.input_pdf):
        print(f"Error: Input file not found: {args.input_pdf}", file=sys.stderr)
        sys.exit(1)

    all_pages = not args.first_only

    success = stamp_pdf_pymupdf(
        input_pdf=args.input_pdf,
        output_pdf=args.output,
        label=args.label,
        bates_prefix=args.prefix,
        start_page=args.start,
        all_pages=all_pages,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
