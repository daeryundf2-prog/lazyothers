# Changelog

## [Unreleased] — 2026-08-30

### Added — Guard Pack 도입 (GUARD_PACK_VERSION 1.0.0, canonical: lazyforensic)

- `hooks.json` 신설 + `plugin.json`에 `hooks` 필드 등록 — 이 플러그인은 지금까지 훅 방어선이 전무했다.
- **markdown_structure_guard.mjs** (`scripts/`): 문서 쓰기 직후 생성 파이프라인 스트리핑(빈 링크 `[](`, 빈 불릿 `-  : `, 빈 강조, 고아 `$수식`, 미닫힘 코드펜스, 표 열 불일치)을 탐지한다. PostToolUse(문서 쓰기 + bash 리다이렉트)에 FAIL_CLOSED 배선. `--check <path…>` 일괄 검사 모드 포함.
- **coverage_audit.mjs** (`scripts/`, synced from canonical): 원문 대조 커버리지 감사 도구. `--source` 원문 파일 없이는 실행을 거부해 순환 감사를 구조적으로 차단하고, 항목별 원문 행 → 산출 위치 매핑 수신증을 남긴다.
- **stop_claim_guard.mjs** (`scripts/`): Stop/SubagentStop 에서 최종 메시지가 완료 선언(완료/전수/100%/모두 통과)인데 반증 가능한 증거(실행 명령, 테스트 수, 산출물 경로, 커밋 SHA)가 없으면 `{"decision":"block"}`으로 증거 첨부를 요구한다. `stop_hook_active` 존중(무한 루프 없음), 페이로드 판독 불가 시 no-op, 절대 non-zero로 빠지지 않는다.
- 배선 정책: 타 플러그인과 동일한 FAIL_CLOSED 원칙(문서 쓰기 가드) + Stop 가드는 정책 미기재(스크립트가 자체적으로 항상 exit 0). 훅 페이로드 규약은 lazyforensic/hallucination_guard와 Antigravity codex-hook 계약을 따른다.
