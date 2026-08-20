---
name: korean-doc-parser
description: "한국 공문서(HWP, HWPX, PDF) 텍스트, 표, 메타데이터 추출 및 마크다운 구조화 스킬. 한컴 오피스 무설치 환경 지원. Triggers: hwp 파싱, hwpx 파싱, 공문서 파싱, 한글 문서 열기, 한글 파서."
---

# Korean Document Parser (HWP / HWPX / PDF)

한컴 오피스나 무거운 바이너리 의존성 없이, 순수 파이썬 및 최신 오픈소스 파서를 활용하여 대한민국 공문서 포맷(`HWPX`, `HWP 5.0`, `PDF`)의 텍스트, 표(Table), 메타데이터를 추출하고 마크다운/JSON으로 변환합니다.

## 핵심 도구

- **스크립트:** `python ${PLUGIN_ROOT}/scripts/parse_korean_doc.py <파일경로> [--markdown] [--output <결과경로>]`
- **지원 포맷:**
  - `HWPX`: OWPML ZIP/XML 구조 파싱 (섹션별 본문, 표, 서식 메타데이터).
  - `HWP 5.0`: OLE Compound 디컴프레션 및 텍스트 추출.
  - `Docling OCR` (선택): 스캔본 PDF의 경우 `docling` 연동을 통한 CJK 고정밀 인식.

## 사용법

```bash
# 1. HWPX 문서 마크다운으로 파싱
python scripts/parse_korean_doc.py "압수문서.hwpx" --markdown --output parsed.md

# 2. JSON 구조화 출력
python scripts/parse_korean_doc.py "계약서.hwp" --output parsed.json
```
