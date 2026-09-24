# CHARTER — lazyothers

## Role
Reporting plane — 한국 법률·문서·PII·금융·문체 도구 묶음.

## Do
- 한국 공문서 파싱(HWP/HWPX/PDF), 표찰, 법률 초안(변호사 검토 전제)
- PII 토큰화·마스킹, 금융 흐름 분석
- 웹 채증(로컬 브라우저 직접 접속만 — 제3자 프록시 금지)

## Don't
- 법원 제출물의 무검토 완성본 주장 금지 — 항상 초안+검토 고지
- 도메인 간 결합은 계약 파일로만 — 직접 런타임 의존 금지
- 검증기 부재 시 검증 통과 시뮬레이션 금지 (not_checked/unavailable 표기)

## Contracts
- Consumes: lazy-evidence-case-v1 (lazyforensic 산출물 편입)
- Produces: 증거설명서·법률 초안·채증 기록
- Vendored: `contracts/` (lazy-contracts, hash-pinned)

## Claims allowed
`observed`, `heuristic`. 문서 산출물은 초안 지위 — `examiner-verified`는 변호사 검토 후에만.
