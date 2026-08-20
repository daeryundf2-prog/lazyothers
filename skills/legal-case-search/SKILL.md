---
name: legal-case-search
description: "국가법령정보센터 및 대법원 판례 검색, 위법성 요건(정보통신망법, 개인정보보호법, 형법 등) 대조 스킬. Triggers: 판례 검색, 법령 조회, 법률 대조, 위법성 검토, korean-law."
---

# Legal Case & Statute Search (Korean Law)

국가법령정보센터 Open API 및 시맨틱 법률 MCP(`korean-law` / `kr-law-mcp`)를 연동하여 포렌식 증거 사실관계와 법률 조문, 대법원 판례 요지를 대조합니다.

## 핵심 도구

- **`korean_law` MCP 도구:**
  - `search_statutes(query)`: 법령 본문 및 조문 검색
  - `search_precedents(query)`: 대법원 및 하급심 판례 요지 검색
  - `get_statute_article(law_name, article_num)`: 특정 법률 조항 상세 조회

## 주요 위법성 대조 영역
- **정보통신망법 제48조/제49조:** 비밀침해, 악성프로그램 유포, 정보통신망 침입.
- **부정경쟁방지법 제18조:** 영업비밀 취득·사용·누설 행위.
- **개인정보보호법 제71조:** 개인정보 무단 유출 및 부정 이용.
- **형법 제314조/제316조:** 업무방해, 비밀침해.
