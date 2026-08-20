# LazyOthers (v0.2.0)

Google Antigravity용 **한국형 리걸테크(Legal-Tech), 공문서 처리(HWP/HWPX) 및 확장 MCP 도구 모음** 플러그인입니다.

## 📦 포함된 도구 및 스킬 (Bundled Skills & Tools)

### 1. 리걸테크 및 공문서 파이프라인 (Legal-Tech & Documents)
*   **`korean-doc-parser`**: 한컴 오피스 무설치 환경에서 `HWPX`, `HWP 5.0`, `PDF` 본문, 표, 메타데이터 추출.
*   **`court-evidence-stiper`**: 대법원 전자소송(ECFS) 표준 규격 `[갑 제O호증]` / `[을 제O호증]` 증거 표찰 박스 및 Bates 번호 스탬핑, `증거설명서` 자동 생성.
*   **`legal-case-search`**: 국가법령정보센터 Open API 및 대법원 판례 시맨틱 검색.

### 2. 확장 MCP 도구 모음 (Bundled MCP Tools)
*   **`kordoc`**: 한국 공문서(HWP/PDF/DOCX) 파싱, 서식 입력, 직인 날인, 비식별화(Redact)
*   **`context7`**: 공식 라이브러리 및 최신 프레임워크 실시간 문서 조회
*   **`grep_app`**: GitHub 오픈소스 전역 코드베이스 고속 검색
*   **`xds`**: 엔지니어링 데이터 및 문서 검색

---

## 🚀 빠른 시작 (Quick Start)

```bash
# 1. HWPX/HWP 문서 마크다운 추출
python scripts/parse_korean_doc.py "압수문서.hwpx" --markdown --output parsed.md

# 2. 대법원 전자소송 서증 표찰 스탬핑
python scripts/stamp_evidence.py "증거.pdf" --output "갑제1호증_증거.pdf" --label "갑 제1호증"

# 3. 증거설명서 마크다운 생성
python scripts/generate_evidence_doc.py --input-json evidence.json --output "증거설명서.md"
```
