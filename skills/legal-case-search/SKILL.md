---
name: legal-case-search
description: "국가법령정보센터 및 대법원 판례 검색, 위법성 요건(정보통신망법, 개인정보보호법, 형법 등) 대조 스킬. Triggers: 판례 검색, 법령 조회, 법률 대조, 위법성 검토, korean-law."
---

# Legal Case & Statute Search (Korean Law)

국가법령정보센터 Open API 및 시맨틱 법률 MCP(`korean-law` / `kr-law-mcp`)를 연동하여 포렌식 증거 사실관계와 법률 조문, 대법원 판례 요지를 대조합니다.

## 핵심 도구

- **`korean_law` MCP 도구 (optional — `lazyforensic` 플러그인 필요):**
  - `search_statutes(query)`: 법령 본문 및 조문 검색
  - `search_precedents(query)`: 대법원 및 하급심 판례 요지 검색
  - `get_statute_article(law_name, article_num)`: 특정 법률 조항 상세 조회

> `lazyforensic` 미설치시 이 스킬은 비활성화됨. `mcp_config.json`의 `korean_law`는 `${PLUGIN_ROOT}/../lazyforensic/korean-law-mcp/build/index.js` 상대경로로 설정, `optional: true`.

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
