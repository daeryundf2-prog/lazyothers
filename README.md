# LazyOthers (v0.5.0)

Google Antigravity용 **한국형 리걸테크(Legal-Tech), 공문서 처리(HWP/HWPX), 한국어 AI 윤문(Humanize KR) 및 확장 MCP 도구 모음** 플러그인입니다.

## 📦 포함된 도구 및 스킬 (Bundled Skills & Tools)

### 1. 한국어 AI 티 제거 및 윤문 엔진 (Humanize KR · im-not-ai)
*   **`humanize-korean`**: LLM(ChatGPT, Claude, Gemini 등)이 작성한 한글 텍스트에서 AI 특유의 번역투, 기계적 병렬, 관용구, 접속사 남발 등 10대 카테고리 71개 패턴을 탐지하여 사실·주장·수치 등 의미는 100% 보존하고 문체와 리듬만 자연스러운 한국어로 재작성. (`scripts/prepare_monolith_input.py`, `scripts/verify_gates.py`)
    *   품질 기준선 계측: `python scripts/eval_baseline.py --k 3` (claude CLI 필요, `--dry-run`으로 계획만 출력) → `scripts/eval_compare.py 이전.json 이후.json`으로 두 스냅샷 대조. 픽스처는 `tests/fixtures.json`
*   **`humanize`**: `/humanize` 단축 명령 엔트리포인트 (Fast 모드 / 정밀 모드)
*   **`humanize-redo`**: `/humanize-redo` 2차 윤문 및 부분 조정 엔트리포인트

### 2. 리걸테크 및 공문서 파이프라인 (Legal-Tech & Documents)
*   **`korean-doc-parser`**: 한컴 오피스 무설치 환경에서 `HWPX`, `HWP 5.0`, `PDF` 본문, 표, 메타데이터 추출. (`scripts/parse_korean_doc.py`)
    *   HWPX(OWPML)는 XML 네임스페이스에 의존하지 않는 로컬 이름 매칭으로 파싱하므로 한컴 버전과 무관하게 동작합니다. 본문 `text`에서 표 셀 내용은 제외되고 `tables`로 별도 제공되어 중복이 없습니다.
    *   HWP 5.0은 `hwp-hwpx-parser` 우선. 미설치/실패 시 OLE 원시 스트림 폴백은 **휴리스틱 추출**이라 깨진 문자가 남고 표/개요 구조는 유실됩니다(결과 JSON `metadata.quality = "rough"`로 표시). 정확한 추출이 필요하면 `pip install hwp-hwpx-parser`.
*   **`court-evidence-stiper`**: 대법원 전자소송(ECFS) 표준 규격 `[갑 제O호증]` / `[을 제O호증]` 증거 표찰 박스 및 Bates 번호 스탬핑, `증거설명서` 자동 생성.
    *   표찰 박스 폭은 라벨 길이에 맞춰 자동 계산되고, `--margin`으로 우측 여백을 조정할 수 있습니다(인장·전송표와 겹칠 때).
    *   증거설명서는 실제 증거 JSON 없이 생성하면 본문 머리/끝에 **"[샘플 자동 생성본 — 법원 제출 금지]"** 워터마크가 들어갑니다.
*   **`legal-case-search`**: 국가법령정보센터 Open API 및 대법원 판례 시맨틱 검색. (`lazyforensic` 플러그인 설치 시 활성화, optional)
*   **`korean-pii-masker`**: 주민등록번호(체크섬 검증)·전화·계좌·이메일 자동 마스킹으로 제출본 비식별화. 날짜 오탐 방지, 처리 통계 리포트. (`scripts/mask_korean_pii.py`)
*   **`court-ruling-analyzer`**: 판결문 섹션 분할(주문/이유/사실), 인용 법령 조문·선고 판례 전수 추출, 쟁점 요약표 골격 생성. (`scripts/analyze_court_ruling.py`)

### 3. 디지털 포렌식·증거 분석 (Forensic & Evidence)
*   **`evidence-integrity-audit`**: 증거 폴더 전수 SHA-256/MD5/SHA-1 감사, 제출용 보고서 기재 해시와의 대조([일치/불일치/미측정] 판정표), 무결성 증명서(Chain of Custody Verification Sheet) 자동 생성. (`scripts/audit_evidence_integrity.py`)
*   **`web-evidence-capture`**: playwright MCP 채증 파이프라인 — 웹 게시물·SNS·기사 캡처 직후 URL·시각·SHA-256을 결합한 채증 기록 생성, 서증 표찰 연계. (`scripts/certify_evidence_file.py`)
*   **`financial-flow-tracer`**: 은행 거래내역(CSV/XLSX) 자금 흐름 분석 — 상대방별 랭킹, 단기 자금 순환(출금→재입금) 의심 감지, 입금원→출금처 홉 체인, Mermaid 흐름도. (`scripts/trace_financial_flow.py`)
*   **`sqlite-evidence-query`**: 압수 SQLite DB 읽기전용 즉석 분석 — 스키마 자동 파악, SELECT 전용 강제, 삭제 레코드 잔존 흔적(본 파일+WAL/저널) 키워드 검색. (`scripts/query_evidence_db.py`)

### 4. 법률 문서 자동화 (Legal Drafting)
*   **`legal-draft-builder`**: 사실관계 메모+증거 목록으로 소장·준비서면·고소장·내용증명 초안 생성 — 청구취지/청구원인 분리, 본문 증거 라벨 자동 인용(입증방법 결합), 변호사 검토 고지 강제. (`scripts/generate_legal_draft.py`)
*   **`court-pdf-binder`**: 표찰된 서증 PDF를 호증별 북마크 트리로 병합하고, ECFS 용량 한계(50MB) 초과 시 자동 분할. 증거설명서 evidence.json 호환. (`scripts/bind_court_pdf.py`)

### 5. 개발자 자원 및 트렌드 허브 (Developer Resources Hub)
*   **`developer-resources`**: 개발자를 위한 4대 자원 디렉터리(`free-for-dev`, `public-apis.io`, `daily-dev`, `devresourc.es`) 통합 검색 및 추천 스킬. (`scripts/query_dev_resources.py`)
    *   **free-for-dev**: 무료 PaaS/SaaS, Cloud Hosting(Vercel/Netlify/Render/Cloudflare), Database(Supabase/Neon/Turso/Upstash), Auth(Clerk), Email(Resend), AI(Groq)
    *   **public-apis.io**: 공개 API 카테고리별 검증 목록 (Auth 타입, HTTPS, CORS 지원 표기)
    *   **daily-dev**: 트렌딩 오픈소스, GitHub Trending, 기술 블로그 및 개발 뉴스 피드
    *   **devresourc.es**: UI 컴포넌트(shadcn/ui), 벡터 아이콘(Lucide), 색상 팔레트(Realtime Colors), Tailwind/Git 치트시트 모음

### 6. 확장 MCP 도구 모음 (Bundled MCP Tools)
*   **`kordoc`**: 한국 공문서(HWP3-5/HWPX/PDF/XLSX/DOCX) 파싱, 서식 입력, 직인 날인, 비식별화(Redact) — npm [`kordoc`](https://www.npmjs.com/package/kordoc) 실제 서버 연결 (`npx -y -p kordoc@4.10.0 kordoc-mcp`, **버전 고정**). 툴 스펙: `mcp/kordoc/*.json` (15개)
*   **`context7`**: 공식 라이브러리 및 최신 프레임워크 실시간 문서 조회 — Upstash 공식 패키지 (`npx -y @upstash/context7-mcp@4.0.4`, 버전 고정)
*   **`playwright`**: 웹 자동화·채증 — 게시물·SNS·기사 스크린샷/PDF 캡처 (microsoft `@playwright/mcp@0.0.79`, 버전 고정). 캡처 직후 `certify_evidence_file.py`로 인증
*   **`sequential-thinking`**: 순차적 심층 추론 — 포렌식 인과관계 역추적·다층 쟁점 분석 (modelcontextprotocol 공식 서버 `@modelcontextprotocol/server-sequential-thinking@2026.7.4`, 버전 고정)
*   **`grep_app`** *(manifest-only)*: GitHub 코드 검색 — 공개 MCP 서버 패키지가 확인되지 않아 `mcp/grep_app/` 스펙만 보관 중 (로드맵)
*   **`xds`** *(manifest-only)*: Astryx XDS 디자인시스템 검색 — 공개 MCP 서버 패키지가 확인되지 않아 `mcp/xds/` 스펙만 보관 중 (로드맵)

> MCP 등록: `plugin.json` → `mcp_config.json` 5개 서버 (kordoc/context7/playwright/sequential-thinking + optional korean_law). grep_app·xds는 서버 미확보로 미등록. `npm run setup`은 검증 + 레거시 미러만 수행.

---

## 🚀 빠른 시작 (Quick Start)

```bash
# 의존성
pip install -r requirements.txt   # olefile, pymupdf, pypdf 등
# 또는 최소: pip install olefile pymupdf

# 1. 한국어 AI 티 제거 및 윤문 (Humanize KR)
# 자연어 트리거: "이 글 AI 티 없애줘", "사람이 쓴 것처럼 윤문해줘", "/humanize"
python scripts/prepare_monolith_input.py --text "초안 텍스트..." --genre essay
python scripts/verify_gates.py --before 01_input.txt --after final.md --genre essay

# 2. HWPX/HWP/PDF 문서 마크다운 추출
python scripts/parse_korean_doc.py "압수문서.hwpx" --markdown --output parsed.md
python scripts/parse_korean_doc.py "계약서.hwp" --output parsed.json
python scripts/parse_korean_doc.py "판결문.pdf" --markdown --output parsed.md

# 3. 대법원 전자소송 서증 표찰 스탬핑 (기본: 전 페이지 표찰 + Bates 번호)
python scripts/stamp_evidence.py "증거.pdf" --output "갑제1호증_증거.pdf" --label "갑 제1호증"
python scripts/stamp_evidence.py "증거.pdf" --output "갑제1호증_증거.pdf" --label "갑 제1호증" --first-only  # 첫 페이지만

# 4. 증거설명서 마크다운 생성 (파일 경로의 전체 SHA-256 자동 기재)
python scripts/generate_evidence_doc.py --input-json evidence.json --output "증거설명서.md" --case-num "2024가합12345"
```

## 설치

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File install.ps1

# macOS / Linux (bash 3.2 호환)
bash install.sh
```

설치 스크립트는 3개 플러그인(`lazyantigravity`, `lazyforensic`, `lazyothers`) 클론/업데이트, korean-law-mcp 빌드, `pip install`, `config.json` 병합까지 수행합니다. (`lazyforensic`은 저장소 URL은 `lazyforensic-.git`이지만 플러그인 디렉터리·plugin.json 이름은 하이픈 없는 `lazyforensic`입니다.)

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
