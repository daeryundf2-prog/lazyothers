#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_korean_doc.py - HWP/HWPX/PDF 한국 공문서 텍스트 및 메타데이터 추출 엔진
"""

import os
import sys
import json
import argparse
import zipfile
import xml.etree.ElementTree as ET


def _escape_md_cell(text: str) -> str:
    """Escape pipe and newlines for markdown table cells."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def parse_hwpx(file_path: str) -> dict:
    """순수 파이썬 ZIP/XML 기반 HWPX 파서 (한컴 오피스/JVM 무설치 지원)"""
    result = {
        "file_path": file_path,
        "format": "HWPX (OWPML)",
        "sections": [],
        "text": "",
        "tables": [],
        "metadata": {}
    }

    with zipfile.ZipFile(file_path, 'r') as z:
        # 1. 메타데이터 (Contents/content.hpf)
        if "Contents/content.hpf" in z.namelist():
            try:
                tree = ET.fromstring(z.read("Contents/content.hpf"))
                for meta in tree.findall(".//{http://purl.org/dc/elements/1.1/}*"):
                    tag = meta.tag.split('}')[-1]
                    result["metadata"][tag] = meta.text or ""
            except Exception as e:
                result["metadata"]["_warning"] = f"Failed to parse content.hpf: {e}"

        # 2. 본문 섹션 (Contents/section0.xml, section1.xml ...)
        section_files = sorted([f for f in z.namelist() if f.startswith("Contents/section") and f.endswith(".xml")])
        if not section_files:
            result["metadata"]["_warning"] = "No section XML found in HWPX"
        full_text_chunks = []

        for s_file in section_files:
            try:
                xml_data = z.read(s_file)
                tree = ET.fromstring(xml_data)
            except Exception as e:
                print(f"[WARN] Failed to parse {s_file}: {e}", file=sys.stderr)
                continue

            # 텍스트 추출 (hp:t 태그)
            texts = [elem.text for elem in tree.findall(".//{http://schemas.hancom.co.kr/owl/hp}t") if elem.text]
            sec_text = "\n".join(texts)
            result["sections"].append({"name": s_file, "text": sec_text})
            full_text_chunks.append(sec_text)

            # 표 추출 (hp:tbl 태그)
            for tbl in tree.findall(".//{http://schemas.hancom.co.kr/owl/hp}tbl"):
                rows = []
                for tr in tbl.findall(".//{http://schemas.hancom.co.kr/owl/hp}tr"):
                    row_cells = []
                    for tc in tr.findall(".//{http://schemas.hancom.co.kr/owl/hp}tc"):
                        cell_texts = [t.text for t in tc.findall(".//{http://schemas.hancom.co.kr/owl/hp}t") if t.text]
                        row_cells.append(" ".join(cell_texts).strip())
                    if row_cells:
                        rows.append(row_cells)
                if rows:
                    result["tables"].append(rows)

        result["text"] = "\n\n".join(full_text_chunks)

    return result


def parse_hwp_legacy(file_path: str) -> dict:
    """구형 HWP (v5.0) 파서 (hwp-hwpx-parser / olefile 기반 또는 안내)"""
    try:
        from hwp_hwpx_parser import HwpParser
        parser = HwpParser(file_path)
        return {
            "file_path": file_path,
            "format": "HWP 5.0 (Binary)",
            "text": parser.get_text(),
            "tables": parser.get_tables() if hasattr(parser, 'get_tables') else [],
            "metadata": {}
        }
    except ImportError:
        # Fallback: olefile 사용
        try:
            import olefile
            import zlib
            ole = olefile.OleFileIO(file_path)
            streams = ole.listdir()
            body_streams = [s for s in streams if s[0] == "BodyText"]
            text_chunks = []
            for b in body_streams:
                stream_data = ole.openstream(b).read()
                try:
                    decompressed = zlib.decompress(stream_data, -15)
                    text = decompressed.decode('utf-16-le', errors='ignore')
                    clean = "".join([c for c in text if c.isprintable() or c in "\n\r\t"])
                    text_chunks.append(clean)
                except Exception:
                    pass
            ole.close()
            return {
                "file_path": file_path,
                "format": "HWP 5.0 (OLE Fallback)",
                "text": "\n".join(text_chunks),
                "metadata": {"note": "Extracted via raw OLE stream decompression"}
            }
        except Exception as e:
            return {
                "file_path": file_path,
                "format": "HWP 5.0",
                "error": f"Failed to parse HWP. Install hwp-hwpx-parser or olefile: {str(e)}"
            }


def parse_pdf(file_path: str) -> dict:
    """PDF 텍스트 및 표 추출 (PyMuPDF 우선, 실패시 pdfminer/pypdf fallback)."""
    result = {
        "file_path": file_path,
        "format": "PDF",
        "sections": [],
        "text": "",
        "tables": [],
        "metadata": {}
    }
    # Try PyMuPDF
    try:
        import fitz
        doc = fitz.open(file_path)
        result["metadata"] = {k: str(v) for k, v in (doc.metadata or {}).items() if v}
        result["metadata"]["page_count"] = str(len(doc))
        chunks = []
        for i, page in enumerate(doc):
            t = page.get_text("text") or ""
            chunks.append(t)
            result["sections"].append({"name": f"page_{i+1}", "text": t})
        result["text"] = "\n\n".join(chunks)
        doc.close()
        return result
    except ImportError:
        pass
    except Exception as e:
        return {"file_path": file_path, "format": "PDF", "error": f"PyMuPDF failed: {e}"}

    # Fallback: pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        result["metadata"]["page_count"] = str(len(reader.pages))
        if reader.metadata:
            for k, v in reader.metadata.items():
                result["metadata"][k] = str(v) if v else ""
        chunks = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            chunks.append(t)
            result["sections"].append({"name": f"page_{i+1}", "text": t})
        result["text"] = "\n\n".join(chunks)
        return result
    except ImportError:
        pass
    except Exception as e:
        return {"file_path": file_path, "format": "PDF", "error": f"pypdf failed: {e}"}

    return {
        "file_path": file_path,
        "format": "PDF",
        "error": "No PDF parser available. Install pymupdf (pip install pymupdf) or pypdf (pip install pypdf)."
    }


def main():
    parser = argparse.ArgumentParser(description="한국 공문서(HWP/HWPX/PDF) 고속 파싱 및 텍스트 추출 도구")
    parser.add_argument("input_file", help="입력 파일 (.hwp, .hwpx, .pdf)")
    parser.add_argument("--output", "-o", help="결과 JSON 저장 경로 (미지정시 stdout 출력)")
    parser.add_argument("--markdown", "-m", action="store_true", help="결과를 마크다운 형식으로 출력")

    args = parser.parse_args()
    file_path = os.path.abspath(args.input_file)

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".hwpx":
        data = parse_hwpx(file_path)
    elif ext == ".hwp":
        data = parse_hwp_legacy(file_path)
    elif ext == ".pdf":
        data = parse_pdf(file_path)
        if "error" in data:
            print(f"Error: {data['error']}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unsupported file extension: {ext} (supported: .hwpx, .hwp, .pdf)", file=sys.stderr)
        sys.exit(1)

    if "error" in data:
        print(f"Error: {data['error']}", file=sys.stderr)
        sys.exit(1)

    if args.markdown:
        md_output = f"# Document Content: {os.path.basename(file_path)}\n\n"
        md_output += f"- **Format:** {data.get('format')}\n"
        if data.get("metadata"):
            md_output += f"- **Metadata:** {json.dumps(data.get('metadata'), ensure_ascii=False)}\n\n"
        md_output += "## Text Body\n\n"
        md_output += data.get("text", "") + "\n\n"
        if data.get("tables"):
            md_output += "## Extracted Tables\n\n"
            for i, tbl in enumerate(data["tables"]):
                md_output += f"### Table {i+1}\n"
                if not tbl:
                    continue
                # Determine column count
                col_count = max(len(r) for r in tbl)
                # Header row (first row as header)
                header = [_escape_md_cell(c) for c in tbl[0]]
                # Pad header if needed
                while len(header) < col_count:
                    header.append("")
                md_output += "| " + " | ".join(header) + " |\n"
                md_output += "| " + " | ".join(["---"] * col_count) + " |\n"
                for row in tbl[1:]:
                    cells = [_escape_md_cell(c) for c in row]
                    while len(cells) < col_count:
                        cells.append("")
                    md_output += "| " + " | ".join(cells) + " |\n"
                # Single-row table (no header separator duplication needed beyond above)
                if len(tbl) == 1:
                    pass
                md_output += "\n"
        if args.output:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(md_output)
            print(f"Saved markdown to: {args.output}")
        else:
            print(md_output)
    else:
        if args.output:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved JSON to: {args.output}")
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
