---
name: developer-resources
description: "개발자를 위한 무료 인프라·PaaS·DB(free-for-dev), 공개 API 목록(public-apis.io), 트렌드 뉴스(daily-dev), UI/디자인/도구 자산(devresourc.es) 통합 조회 및 추천 스킬. Triggers: free-for-dev, public-apis, public-apis.io, daily-dev, daily.dev, devresourc.es, devresources, 개발자 자원, 무료 호스팅, 무료 DB, 공개 API 추천, 개발 도구 모음."
---

# Developer Resources Hub (개발자 자원 및 트렌드 허브)

개발에 필요한 **무료 인프라/SaaS(free-for-dev)**, **공개 API(public-apis.io)**, **기술 트렌드/뉴스(daily-dev)**, **UI/디자인/치트시트 자산(devresourc.es)** 4대 플랫폼의 데이터베이스를 실시간으로 조회하고 최적의 스택 및 도구를 추천합니다.

---

## 📌 지원 플랫폼 4종

### 1. `free-for-dev`
- **목적:** 개발자를 위한 무료 Tier (Cloud, Hosting, Database, Auth, Storage, Email, AI 등) 수록
- **대표 카테고리:**
  - **Hosting & PaaS:** Vercel (Next.js/Frontend), Netlify, Render (Docker/PostgreSQL), Cloudflare Pages/Workers
  - **Database & BaaS:** Supabase (PostgreSQL/BaaS), Neon (Serverless Postgres Branching), Turso (Edge libSQL), Upstash (Serverless Redis/Kafka)
  - **Auth & Storage:** Clerk (10K MAU 무료), Cloudflare R2 / Backblaze B2 (무료 10GB+)
  - **AI & Email:** Groq Cloud (초고속 LLM 추론 API), Resend (월 3,000건 이메일)

### 2. `public-apis.io`
- **목적:** 인증 방식(No Auth / API Key / OAuth), HTTPS, CORS 지원 여부가 검증된 공개 API 디렉터리
- **대표 카테고리:**
  - **Weather & Geo:** Open-Meteo (No Auth 기후예보), REST Countries, IP-API
  - **Finance & DevTools:** ExchangeRate-API (환율), JSONPlaceholder (가짜 REST API 테스트)
  - **AI & ML:** Hugging Face Inference API (오픈소스 모델 추론)

### 3. `daily-dev`
- **목적:** 최신 개발 트렌드, 엔지니어링 블로그, 오픈소스 급상승 프로젝트 추적
- **대표 채널:**
  - **daily.dev Feed:** 600개 이상 테크 블로그 및 개발 이슈 큐레이션
  - **GitHub Trending Repositories:** 오늘/이번 주 언어별 급상승 오픈소스
  - **Hacker News & TLDR Tech:** 기술 토론 및 5분 일간 요약 뉴스레터

### 4. `devresourc.es`
- **목적:** UI 컴포넌트, 아이콘, 디자인 시스템, 색상 툴, 치트시트, 보일러플레이트 자산 모음
- **대표 자원:**
  - **UI & Icons:** shadcn/ui (Radix UI + Tailwind), Lucide Icons (1,000+ 벡터 아이콘)
  - **Design & Colors:** Realtime Colors (실시간 컬러 팔레트 테스트), Happy Hues
  - **Cheat Sheets:** Tailwind Cheat Sheet, DevHints.io (Git, Docker, Regex 요약 카드)

---

## 🛠️ 스크립트 실행 명령어

`SKILL_ROOT` 스크립트를 사용하여 커맨드라인에서 데이터베이스를 즉시 조회합니다.

```bash
# 1. 현황 및 플랫폼별 대표 카테고리 요약
python scripts/query_dev_resources.py --summary

# 2. 키워드 검색 (예: postgres, auth, ai, tailwind 등)
python scripts/query_dev_resources.py --query postgres
python scripts/query_dev_resources.py --query auth

# 3. 특정 플랫폼으로 필터링
python scripts/query_dev_resources.py --platform free-for-dev
python scripts/query_dev_resources.py --platform public-apis.io
python scripts/query_dev_resources.py --platform devresourc.es

# 4. 카테고리 및 JSON 구조화 출력
python scripts/query_dev_resources.py --category "Hosting" --json
```

---

## 💡 사용자 요청 대응 가이드

1. **"무료 호스팅이나 무료 DB 추천해줘"**
   - `python scripts/query_dev_resources.py --platform free-for-dev` 실행 후 사용자의 스택(Next.js, Python, Docker 등)에 맞춰 **Vercel, Render, Supabase, Neon** 등의 무료 용량과 혜택을 비교 추천.

2. **"테스트에 쓸 수 있는 공개 API 있어?"**
   - `python scripts/query_dev_resources.py --platform public-apis.io` 실행 후 Auth 요구 여부(`No Auth`), HTTPS, CORS 지원 여부를 함께 명시하여 추천.

3. **"UI 디자인이나 색상 팔레트, 아이콘 추천해줘"**
   - `python scripts/query_dev_resources.py --platform devresourc.es` 실행 후 **shadcn/ui, Lucide Icons, Realtime Colors**의 URL과 사용 목적 안내.

4. **"요즘 트렌딩 오픈소스나 기술 뉴스 어디서 봐?"**
   - `python scripts/query_dev_resources.py --platform daily-dev` 실행 후 **daily.dev, GitHub Trending, Hacker News** 가이드 제공.
