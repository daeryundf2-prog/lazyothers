---
name: legal-draft-builder
description: "사실관계 메모와 입증자료 목록으로 대법원 전자소송 규격 소장·준비서면·고소장·내용증명 초안을 생성하는 스킬. 청구취지/청구원인 분리, 증거 자동 인용(입증방법 결합), 변호사 검토 고지 강제. Triggers: 소장 초안, 준비서면, 고소장 작성, 내용증명, 법률 문서 초안, 답변서."
---

# Legal Draft Builder — 법률 문서 초안 생성기

사실관계와 증거 목록이 정리돼 있으면 전자소송 규격 형식의 법률 문서 **초안**을
만든다. 산출물은 항상 "변호사 검토 전 제출 금지" 고지를 포함하며, 이 고지는
끌 수 없다.

## 핵심 도구

```bash
python ${PLUGIN_ROOT}/scripts/generate_legal_draft.py --input-json draft.json -o 소장_초안.md
```

입력 JSON 구조(필드는 `generate_legal_draft.py` docstring 참조):

```json
{
  "type": "소장",                     // 소장 | 준비서면 | 고소장 | 내용증명
  "case_info": {"court": "서울중앙지방법원", "plaintiff": "홍길동", "defendant": "주식회사 XXX"},
  "claims": ["대여금 원금 10,000,000원 및 이에 대한 지연손해금"],
  "facts": [
    {"heading": "1. 대여 관계의 성립",
     "paragraphs": ["...금원을 전달하였다(갑 제1호증). ..."],
     "evidence": []}
  ],
  "evidence_list": [{"label": "갑 제1호증", "title": "차용증"}]
}
```

## 작동 방식

- **청구취지 / 청구원인 분리**: 소장은 `claims`를 청구취지로, `facts`를
  청구원인(사실관계)으로 배치한다. 준비서면은 주장·항변 구조, 고소장은
  범죄사실·고소 이유 구조, 내용증명은 경위·요구 구조.
- **증거 자동 인용**: 본문에 `갑 제1호증`(공백 유무 무관, `호증의 1` 지원)이
  나오면 증거 목록의 서증명을 찾아 `*입증방법: 갑 제1호증, 차용증*` 문장을
  문단 뒤에 결합한다. `facts[].evidence`로 명시 지정도 가능하다.
- **고지 강제**: 헤더와 푸터에 변호사 검토 전제 고지가 들어간다. 제거 금지.

## 법률 사실성 검증 (Anti-Hallucination Gate)

`generate_legal_draft.py`는 대한민국 주요 법령의 조문 상한 경계(`STATUTE_BOUNDS`, 예: 민법 1118조, 형법 372조)와 대법원 판례 연도(1948~2026년) 및 사건부호 규칙을 기계적으로 자동 검증합니다.

```bash
# 초안 생성 시 자동 사실성 검증 수행 (허위 조문이나 미래 연도 판례 발견 시 즉각 차단)
python ${PLUGIN_ROOT}/scripts/generate_legal_draft.py --input-json draft.json -o 소장_초안.md

# 작성된 마크다운 초안의 조문/판례 사실성 단독 검사
python ${PLUGIN_ROOT}/scripts/verify_legal_factuality.py 소장_초안.md --json
```

- 허위 조문(예: 민법 제1500조) 또는 가짜 판례가 감지되면 exit 1로 생성이 차단됩니다.
- 포스트툴유즈 훅(`legal_factuality_guard.mjs`) 역시 새로 쓰인 법률 문서에 대해 FAIL_CLOSED 원칙으로 위반을 차단합니다.

## HWPX 변환 (제출용 서식이 필요할 때)

마크다운 초안은 `kordoc` MCP의 `generate_document`로 HWPX로 변환할 수 있다
("이 마크다운을 공문서로 뽑아줘"). 변환 후에도 표찰(`stamp_evidence.py`)과
해시(`audit_evidence_integrity.py`)는 원본·제출본 각각 관리한다.

## 책임 경계

- 법률 요건사실 구성(청구원인 구조), 관할, 소제기 기간, 처벌 희망 여부 등은
  **변호사 판단 사항**이다. 본 스킬은 형식화된 초안을 만들 뿐 법률 자문이
  아니다. 요건사실이 비어 있으면 `{...}` 플레이스홀더로 표시되므로, 사람이
  채운 뒤 검토를 거쳐야 한다.
