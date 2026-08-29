# LazyOthers (v0.3.0)

Google Antigravity용 **한국형 리걸테크(Legal-Tech), 공문서 처리(HWP/HWPX) 및 확장 MCP 도구 모음** 플러그인입니다.

## 📦 포함된 도구 및 스킬 (Bundled Skills & Tools)

### 1. 리걸테크 및 공문서 파이프라인 (Legal-Tech & Documents)
*   **`korean-doc-parser`**: 한컴 오피스 무설치 환경에서 `HWPX`, `HWP 5.0`, `PDF` 본문, 표, 메타데이터 추출. (`scripts/parse_korean_doc.py`)
    *   HWPX(OWPML)는 XML 네임스페이스에 의존하지 않는 로컬 이름 매칭으로 파싱하므로 한컴 버전과 무관하게 동작합니다. 본문 `text`에서 표 셀 내용은 제외되고 `tables`로 별도 제공되어 중복이 없습니다.
    *   HWP 5.0은 `hwp-hwpx-parser` 우선. 미설치/실패 시 OLE 원시 스트림 폴백은 **휴리스틱 추출**이라 깨진 문자가 남고 표/개요 구조는 유실됩니다(결과 JSON `metadata.quality = "rough"`로 표시). 정확한 추출이 필요하면 `pip install hwp-hwpx-parser`.
*   **`court-evidence-stiper`**: 대법원 전자소송(ECFS) 표준 규격 `[갑 제O호증]` / `[을 제O호증]` 증거 표찰 박스 및 Bates 번호 스탬핑, `증거설명서` 자동 생성.
    *   표찰 박스 폭은 라벨 길이에 맞춰 자동 계산되고, `--margin`으로 우측 여백을 조정할 수 있습니다(인장·전송표와 겹칠 때).
    *   증거설명서는 실제 증거 JSON 없이 생성하면 본문 머리/끝에 **"[샘플 자동 생성본 — 법원 제출 금지]"** 워터마크가 들어갑니다.
*   **`legal-case-search`**: 국가법령정보센터 Open API 및 대법원 판례 시맨틱 검색. (`lazyforensic-` 플러그인 설치 시 활성화, optional)

### 2. 확장 MCP 도구 모음 (Bundled MCP Tools)
*   **`kordoc`**: 한국 공문서(HWP3-5/HWPX/PDF/XLSX/DOCX) 파싱, 서식 입력, 직인 날인, 비식별화(Redact) — npm [`kordoc`](https://www.npmjs.com/package/kordoc) 실제 서버 연결 (`npx -y -p kordoc@4.10.0 kordoc-mcp`, **버전 고정**). 툴 스펙: `mcp/kordoc/*.json` (15개)
*   **`context7`**: 공식 라이브러리 및 최신 프레임워크 실시간 문서 조회 — Upstash 공식 패키지 (`npx -y @upstash/context7-mcp@4.0.4`, 버전 고정)
*   **`grep_app`** *(manifest-only)*: GitHub 코드 검색 — 현재 공개 MCP 서버 패키지가 없어 `mcp/grep_app/` 스펙만 보관 중 (로드맵)
*   **`xds`** *(manifest-only)*: Astryx XDS 디자인시스템 검색 — 공개 MCP 서버 미확보, `mcp/xds/` 스펙만 보관 중 (로드맵)

> MCP 등록: `plugin.json` → `mcp_config.json` 3개 서버 (kordoc/context7 + optional korean_law). `npm run setup`은 검증 + 레거시 미러만 수행.

---

## 🚀 빠른 시작 (Quick Start)

```bash
# 의존성
pip install -r requirements.txt   # olefile, pymupdf, pypdf 등
# 또는 최소: pip install olefile pymupdf

# 1. HWPX/HWP/PDF 문서 마크다운 추출
python scripts/parse_korean_doc.py "압수문서.hwpx" --markdown --output parsed.md
python scripts/parse_korean_doc.py "계약서.hwp" --output parsed.json
python scripts/parse_korean_doc.py "판결문.pdf" --markdown --output parsed.md

# 2. 대법원 전자소송 서증 표찰 스탬핑 (기본: 전 페이지 표찰 + Bates 번호)
python scripts/stamp_evidence.py "증거.pdf" --output "갑제1호증_증거.pdf" --label "갑 제1호증"
python scripts/stamp_evidence.py "증거.pdf" --output "갑제1호증_증거.pdf" --label "갑 제1호증" --first-only  # 첫 페이지만

# 3. 증거설명서 마크다운 생성 (파일 경로의 전체 SHA-256 자동 기재)
python scripts/generate_evidence_doc.py --input-json evidence.json --output "증거설명서.md" --case-num "2024가합12345"
```

## 설치

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File install.ps1

# macOS / Linux (bash 3.2 호환)
bash install.sh
```

설치 스크립트는 3개 플러그인(`lazyantigravity`, `lazyforensic-`, `lazyothers`) 클론/업데이트, korean-law-mcp 빌드, `pip install`, `config.json` 병합까지 수행합니다.

## 요구사항

- Python >=3.8, Node.js >=18
- 한글 표찰 폰트: 시스템 폰트를 자동 탐색합니다 (macOS AppleSDGothicNeo / Windows 맑은고딕 / Linux NanumGothic). 해당 폰트가 없으면 `scripts/NotoSansKR-Regular.ttf` 또는 `.otf`를 배치하세요. 폰트가 전혀 없으면 한글이 깨질 수 있습니다.

## 🧪 테스트

```bash
pip install pytest
pytest -q
```

GitHub Actions CI가 `.github/workflows/ci.yml`에서 push/PR마다 pytest(한글 폰트 설치 포함 — 표찰 테스트가 스킵 없이 실행됨), `sync-mcp.mjs` 검증, 전체 JSON 유효성 검사를 수행합니다.

## 🗺️ 로드맵 (다음 작업)

- [ ] `grep_app` / `xds`: 공개 MCP 서버 확보 또는 자체 브리지 구현 시 `mcp_config.json` 재등록
- [ ] `kordoc` 고급 기능 검증: `place_seal`, `redact_document`, `generate_document` 등 나머지 툴 실문서 통합 테스트
- [ ] 스캔본 PDF OCR 연동 (`docling` 등 — `requirements.txt` 주석 참조)
- [ ] 실제 HWP 5.0 바이너리 샘플 파일 기반 회귀 테스트
