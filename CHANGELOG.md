# Changelog

## [Unreleased] — 2026-08-30

### Added — Section 5.1 #2 공공기관 및 폐지 부처 명칭 날조 차단 & Section 6 Legal Claim Ledger 프로토콜

- `scripts/verify_legal_factuality.py`: 가짜 법원 명칭(`FABRICATED_COURT_RE`, e.g. 서울민사지방법원, 한국연방법원 등) 및 가짜 공공기관/위원회(`FABRICATED_AGENCY_RE`, e.g. 사이버수사처, 디지털포렌식청, 개인정보보호청 등)를 한국어 조사/접미사(`와`, `과`, `도`, `만`, `은`, `는`, `이`, `가` 등) 전수 결합 경계로 완벽 탐지. 폐지된 25개 구 정부 부처명(`ABOLISHED_GOV_AGENCIES`)의 현행 승계 부처 병기 시 경고 처리 및 `--allow-historical` 플래그 지원. `verify_legal_text`에 `claim_ledger_path` 연동 직접 지원.
- `scripts/verify_claim_ledger.py`: Section 6 Legal Claim Ledger 프로토콜 검증기 신설 — 2개 이상의 독립 도메인(IPv4 직접 지원) 또는 2개 이상의 독립 법령/판례 출처(민법·형법뿐만 아니라 근로기준법, 저작권법, 특허법, 자본시장법 등 26대 법률 전수 지원), 서문/메타데이터 테이블 선행 마크다운 문서 파싱 강건화, 명시적 반증 검색(Counter-Search) / 반대 법리 검증, 1차 출처 명시, 소장/준비서면 인용 잠금(`[Claim X]`는 `VERIFIED` 상태만 인용 허용) 검증.
- `scripts/generate_legal_draft.py`: `--claim-ledger` CLI 옵션 및 `generate()` 파라미터 신설, 문자열 사실관계 목록 입력 호환성 확장.
- `scripts/legal_factuality_guard.mjs`: `claim-ledger.md` / `claim_ledger.md` 자동 탐지 시 `--claim-ledger` 연동 검증 자동 실행.
- `scripts/verify_legal_factuality.py --claim-ledger <path>`: 법률 문서 초안 검증 시 Claim Ledger 연계 검증 지원.
- 단위 테스트 신설 및 보강: `tests/test_verify_legal_claim_ledger.py` 신설(9개), `tests/test_verify_legal_factuality.py`에 날조 법원/기관 조사 결합, 역사적 부처 병기, 소장 생성기 원장 연동 테스트 추가.

### Added — Guard Pack 도입 (GUARD_PACK_VERSION 1.0.0, canonical: lazyforensic)

- `hooks.json` 신설 + `plugin.json`에 `hooks` 필드 등록 — 이 플러그인은 지금까지 훅 방어선이 전무했다.
- **markdown_structure_guard.mjs** (`scripts/`): 문서 쓰기 직후 생성 파이프라인 스트리핑(빈 링크 `[](`, 빈 불릿 `-  : `, 빈 강조, 고아 `$수식`, 미닫힘 코드펜스, 표 열 불일치)을 탐지한다. PostToolUse(문서 쓰기 + bash 리다이렉트)에 FAIL_CLOSED 배선. `--check <path…>` 일괄 검사 모드 포함.
- **coverage_audit.mjs** (`scripts/`, synced from canonical): 원문 대조 커버리지 감사 도구. `--source` 원문 파일 없이는 실행을 거부해 순환 감사를 구조적으로 차단하고, 항목별 원문 행 → 산출 위치 매핑 수신증을 남긴다.
- **stop_claim_guard.mjs** (`scripts/`): Stop/SubagentStop 에서 최종 메시지가 완료 선언(완료/전수/100%/모두 통과)인데 반증 가능한 증거(실행 명령, 테스트 수, 산출물 경로, 커밋 SHA)가 없으면 `{"decision":"block"}`으로 증거 첨부를 요구한다. `stop_hook_active` 존중(무한 루프 없음), 페이로드 판독 불가 시 no-op, 절대 non-zero로 빠지지 않는다.
- 배선 정책: 타 플러그인과 동일한 FAIL_CLOSED 원칙(문서 쓰기 가드) + Stop 가드는 정책 미기재(스크립트가 자체적으로 항상 exit 0). 훅 페이로드 규약은 lazyforensic/hallucination_guard와 Antigravity codex-hook 계약을 따른다.
