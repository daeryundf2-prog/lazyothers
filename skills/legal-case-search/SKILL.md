---
name: legal-case-search
description: "국가법령정보센터 및 대법원 판례 검색, 위법성 요건(정보통신망법, 개인정보보호법, 형법 등) 대조 스킬. Triggers: 판례 검색, 법령 조회, 법률 대조, 위법성 검토, korean-law."
---

# Legal Case & Statute Search (Korean Law)

국가법령정보센터 Open API 및 시맨틱 법률 MCP(`korean-law` / `kr-law-mcp`)를 연동하여 포렌식 증거 사실관계와 법률 조문, 대법원 판례 요지를 대조합니다.

## 핵심 도구

- **`korean_law` MCP 도구 (optional — `lazyforensic` 플러그인 필요, 실제 등록 도구명 기준):**
  - `search_law`: 법령 검색 (정확매칭 + 개정 이력, 법령 MST 반환)
  - `get_law_text`: 법령 MST의 본문·조문 전문 조회
  - `search_decisions` / `get_decision_text`: 판례 검색 및 판결문 전문 조회
  - 기타: `ordinance_radar`, `get_annexes`, `legal_research`, `legal_analysis`, `discover_tools`, `execute_tool` (총 10개)

> `korean_law_mcp_wrapper.mjs`가 `lazyforensic`의 전체 API 서버 또는 `lazyantigravity`의 오프라인 랜드마크 법률/판례 DB를 자동 감지하여 투명하게 연동합니다.
> 작성된 모든 법률 검토 결과물은 `verify_legal_factuality.py`를 통해 실존 법령 상한선 및 판례 번호 규칙에 대해 기계적으로 전수 감사됩니다.

## 기계적 사실성 게이트

```bash
python ${PLUGIN_ROOT}/scripts/verify_legal_factuality.py 법률검토서.md --json
```

## 설치

```bash
# 별도 플러그인 (저장소 URL에 하이픈 있음, 플러그인 디렉터리명은 하이픈 없음)
git clone https://github.com/daeryundf2-prog/lazyforensic-.git ~/.gemini/config/plugins/lazyforensic

# korean-law-mcp 빌드 (build/index.js 생성)
cd ~/.gemini/config/plugins/lazyforensic/korean-law-mcp
npm install && npm run build
```

## 주요 위법성 대조 영역
- **정보통신망법 제48조/제49조:** 비밀침해, 악성프로그램 유포, 정보통신망 침입.
- **부정경쟁방지법 제18조:** 영업비밀 취득·사용·누설 행위.
- **개인정보보호법 제71조:** 개인정보 무단 유출 및 부정 이용.
- **형법 제314조/제316조:** 업무방해, 비밀침해.
