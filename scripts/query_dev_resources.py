#!/usr/bin/env python3
"""
query_dev_resources.py — 개발자 자원 및 트렌드 허브 (Developer Resources Hub)

통합 대상 4대 플랫폼:
1. free-for-dev (무료 SaaS, PaaS, IaaS, DB, 인프라)
2. public-apis.io (공개 API 디렉터리: Auth, HTTPS, CORS 정보 포함)
3. daily-dev (개발자 기술 뉴스, 트렌딩 레포지토리, 생태계 동향)
4. devresourc.es (UI 컴포넌트, 아이콘, 색상/디자인 툴, 보일러플레이트, 치트시트)
"""

import argparse
import json
import re
import sys
from typing import Dict, List, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEV_RESOURCES_DATA: Dict[str, List[Dict[str, Any]]] = {
    "free-for-dev": [
        {
            "name": "Vercel",
            "category": "Hosting & PaaS",
            "url": "https://vercel.com",
            "description": "Next.js 및 정적/서버리스 웹 애플리케이션 무료 호스팅, 자동 SSL 및 글로벌 Edge CDN 제공",
            "free_tier": "무료 혜택: 100GB 데이터 전송량/월, 서버리스 함수 실행 100K/월, 커스텀 도메인 무료 연결",
            "tags": ["frontend", "nextjs", "hosting", "serverless", "cdn"]
        },
        {
            "name": "Netlify",
            "category": "Hosting & PaaS",
            "url": "https://www.netlify.com",
            "description": "정적 사이트 및 Jamstack 앱용 CI/CD 자동 빌드 호스팅, Serverless Functions 및 Forms 지원",
            "free_tier": "무료 혜택: 100GB 대역폭/월, 300 빌드분/월, 100K 폼 전송/월",
            "tags": ["jamstack", "static-site", "ci-cd", "hosting"]
        },
        {
            "name": "Render",
            "category": "Hosting & PaaS",
            "url": "https://render.com",
            "description": "Node.js, Python, Go, Docker 컨테이너 및 PostgreSQL/Redis 무료 호스팅 플랫폼",
            "free_tier": "무료 혜택: 웹 서비스 750시간/월(휴면 스핀다운), 무료 PostgreSQL DB (90일 유지)",
            "tags": ["paas", "docker", "backend", "postgres", "redis"]
        },
        {
            "name": "Cloudflare Pages & Workers",
            "category": "Hosting & Edge",
            "url": "https://pages.cloudflare.com",
            "description": "글로벌 Edge 네트워크 기반 정적 호스팅 및 Serverless Worker 스크립트 실행 환경",
            "free_tier": "무료 혜택:무제한 대역폭, 무제한 요청, Worker 하루 100K 요청 무료",
            "tags": ["edge", "serverless", "unlimited-bandwidth", "cdn"]
        },
        {
            "name": "Supabase",
            "category": "Database & BaaS",
            "url": "https://supabase.com",
            "description": "Firebase 대안 오픈소스 PostgreSQL 기반 BaaS (인증, 실시간 구독, Storage, Edge Functions)",
            "free_tier": "무료 혜택: 2개 무료 프로젝트, 500MB DB 용량, 1GB 파일 저장소, 50K MAU 인증 무료",
            "tags": ["database", "postgres", "baas", "auth", "storage"]
        },
        {
            "name": "Neon",
            "category": "Database",
            "url": "https://neon.tech",
            "description": "서버리스 관리형 PostgreSQL (Database Branching, 자동 스케일 온/오프 지원)",
            "free_tier": "무료 혜택: 0.5GB 스토리지, 무제한 데이터베이스 분기(Branching), 컴퓨팅 자동 일시정지",
            "tags": ["postgres", "serverless-db", "branching", "sql"]
        },
        {
            "name": "Turso",
            "category": "Database",
            "url": "https://turso.tech",
            "description": "libSQL(SQLite 포크) 기반 분산 Edge 데이터베이스 (초저지연 글로벌 복제)",
            "free_tier": "무료 혜택: 9GB 스토리지, 500개 DB 생성 가능, 10억 읽기 쿼리/월",
            "tags": ["sqlite", "edge-db", "libsql", "fast"]
        },
        {
            "name": "Upstash",
            "category": "Database & Messaging",
            "url": "https://upstash.com",
            "description": "Serverless Redis 및 Kafka, QStash 메시지 큐 (HTTP/REST 규격 지원)",
            "free_tier": "무료 혜택: Redis 10K 요청/일, QStash 500 요청/일 무료",
            "tags": ["redis", "kafka", "queue", "cache", "serverless"]
        },
        {
            "name": "Clerk",
            "category": "Authentication",
            "url": "https://clerk.com",
            "description": "React, Next.js, Vue용 완성형 사용자 인증 및 권한 관리(User Management) UI 컴포넌트",
            "free_tier": "무료 혜택: 월간 활성 사용자(MAU) 10,000명까지 완전 무료",
            "tags": ["auth", "user-management", "sso", "mfa", "nextjs"]
        },
        {
            "name": "Resend",
            "category": "Email & Communication",
            "url": "https://resend.com",
            "description": "개발자 친화적 트랜잭션 이메일 전송 API (React Email 연동 지원)",
            "free_tier": "무료 혜택: 월 3,000건 이메일 전송 (일 100건 제한), 커스텀 도메인 1개",
            "tags": ["email", "api", "smtp", "transactional-email"]
        },
        {
            "name": "Groq Cloud",
            "category": "AI Infrastructure",
            "url": "https://groq.com",
            "description": "LPU(Language Processing Unit) 인프라 기반 초고속 LLM 추론 API (Llama 3, Mixtral 등)",
            "free_tier": "무료 혜택: 일일 제한 분당/일일 토큰 무료 레이트 리밋 분배 (실시간 초고속 답변)",
            "tags": ["ai", "llm", "inference", "groq", "llama3"]
        },
        {
            "name": "Sentry",
            "category": "Monitoring & Logging",
            "url": "https://sentry.io",
            "description": "실시간 실시간 에러 트래킹 및 성능 모니터링 디버깅 도구",
            "free_tier": "무료 혜택: 월 5,000개 에러 이벤트, 10,000개 트랜잭션 트레이싱 무료",
            "tags": ["error-tracking", "monitoring", "apm", "debugging"]
        }
    ],
    "public-apis.io": [
        {
            "name": "Open-Meteo",
            "category": "Weather & Climate",
            "url": "https://open-meteo.com",
            "description": "무료 일기예보 및 기후 데이터 API (로그인/API 키 미요구, 고해상도 수치예보)",
            "auth": "No Auth",
            "https": True,
            "cors": "Yes",
            "tags": ["weather", "forecast", "climate", "geocoding"]
        },
        {
            "name": "ExchangeRate-API",
            "category": "Finance & Currency",
            "url": "https://www.exchangerate-api.com",
            "description": "실시간 세계 환율 환전 및 통화 수치 변환 데이터를 제공하는 REST API",
            "auth": "API Key",
            "https": True,
            "cors": "Yes",
            "tags": ["finance", "currency", "forex", "exchange-rate"]
        },
        {
            "name": "REST Countries",
            "category": "Geocoding & Data",
            "url": "https://restcountries.com",
            "description": "전 세계 국가 정보(국기 이미지, 통화, 수도, 언어, 인구수) 국가 표준 REST 데이터 API",
            "auth": "No Auth",
            "https": True,
            "cors": "Yes",
            "tags": ["countries", "geography", "data", "flags"]
        },
        {
            "name": "JSONPlaceholder",
            "category": "DevTools & Testing",
            "url": "https://jsonplaceholder.typicode.com",
            "description": "프론트엔드 개발 및 테스트용 가짜(Fake) REST API (Posts, Comments, Albums, Users)",
            "auth": "No Auth",
            "https": True,
            "cors": "Yes",
            "tags": ["mock", "testing", "fake-api", "rest"]
        },
        {
            "name": "Hugging Face Inference API",
            "category": "AI & Machine Learning",
            "url": "https://huggingface.co/docs/api-inference",
            "description": "수만 개의 오픈소스 AI 모델(NLP, 비전, 오디오)을 즉시 호출하는 추론 API",
            "auth": "API Key",
            "https": True,
            "cors": "Yes",
            "tags": ["ai", "nlp", "machine-learning", "models"]
        },
        {
            "name": "IP-API",
            "category": "Geocoding & Security",
            "url": "https://ip-api.com",
            "description": "IP 주소 기반 국가, 도시, ISP, 위도/경도 위치 추적 지오로케이션 API",
            "auth": "No Auth",
            "https": False,
            "cors": "Yes",
            "tags": ["ip", "geolocation", "security", "network"]
        }
    ],
    "daily-dev": [
        {
            "name": "daily.dev Feed",
            "category": "Developer News & Trends",
            "url": "https://daily.dev",
            "description": "전 세계 600개 이상 엔지니어링 블로그, GitHub 이슈, 테크 뉴스를 맞춤형 커스텀 피드로 제공",
            "tags": ["news", "tech-blog", "rss", "community", "trends"]
        },
        {
            "name": "GitHub Trending Repositories",
            "category": "Open Source Trends",
            "url": "https://github.com/trending",
            "description": "오늘/이번 주 가장 빠르게 별(Star)을 얻고 있는 언어별 급상승 오픈소스 프로젝트 트래커",
            "tags": ["github", "trending", "open-source", "popular"]
        },
        {
            "name": "Hacker News (Y Combinator)",
            "category": "Tech News & Discussion",
            "url": "https://news.ycombinator.com",
            "description": "스타트업, 컴퓨터 과학, 소프트웨어 엔지니어링 및 기술 심층 토론 커뮤니티 피드",
            "tags": ["hacker-news", "startups", "tech", "discussion"]
        },
        {
            "name": "TLDR Tech Newsletter",
            "category": "Newsletter",
            "url": "https://tldr.tech",
            "description": "매일 5분 안에 읽는 브레이킹 테크, 코딩 프레임워크, 과학 기술 일간 요약 뉴스레터",
            "tags": ["newsletter", "summary", "daily-brief", "tech"]
        }
    ],
    "devresourc.es": [
        {
            "name": "shadcn/ui",
            "category": "UI Components",
            "url": "https://ui.shadcn.com",
            "description": "Radix UI + Tailwind CSS 기반 복사-붙여넣기 형태의 재사용 가능한 리액트 UI 컴포넌트 모음",
            "tags": ["ui", "react", "tailwind", "components", "accessible"]
        },
        {
            "name": "Lucide Icons",
            "category": "Icons",
            "url": "https://lucide.dev",
            "description": "Feather Icons의 커뮤니티 포크, 1,000개 이상의 일관되고 정교한 벡터 벡터 아이콘 팩",
            "tags": ["icons", "svg", "vector", "react-icons"]
        },
        {
            "name": "Realtime Colors",
            "category": "Design & Colors",
            "url": "https://www.realtimecolors.com",
            "description": "실시간으로 실제 웹사이트 템플릿에 컬러 팔레트를 대입해 수치 및 명암비를 테스트하는 툴",
            "tags": ["colors", "palette", "design", "contrast", "preview"]
        },
        {
            "name": "Tailwind Cheat Sheet",
            "category": "Cheat Sheets",
            "url": "https://nerdcave.com/tailwind-cheat-sheet",
            "description": "Tailwind CSS 전 클래스명, 유틸리티 속성, 반응형 중단점 검색 가능한 퀵 렌더 치트시트",
            "tags": ["cheatsheet", "tailwind", "css", "quick-reference"]
        },
        {
            "name": "DevHints (TLDR Cheat Sheets)",
            "category": "Cheat Sheets",
            "url": "https://devhints.io",
            "description": "Git, Docker, Bash, React, Regex, Markdown 등 핵심 키워드별 일목요연 요약 카드 치트시트",
            "tags": ["cheatsheet", "devhints", "git", "docker", "quickref"]
        },
        {
            "name": "Happy Hues",
            "category": "Design & Colors",
            "url": "https://www.happyhues.co",
            "description": "맥락(Context)에 어울리는 색상 배치 가이드 및 웹 UI 추천 전용 컬러 팔레트 사이트",
            "tags": ["colors", "ui-design", "palettes", "inspiration"]
        }
    ]
}


def search_resources(
    query: Optional[str] = None,
    platform: Optional[str] = None,
    category: Optional[str] = None,
    as_json: bool = False
) -> str:
    """자원 검색 및 필터링 수행"""
    results: List[Dict[str, Any]] = []

    target_platforms = [platform] if platform and platform in DEV_RESOURCES_DATA else list(DEV_RESOURCES_DATA.keys())

    query_pattern = re.compile(re.escape(query), re.IGNORECASE) if query else None
    category_pattern = re.compile(re.escape(category), re.IGNORECASE) if category else None

    for plat in target_platforms:
        items = DEV_RESOURCES_DATA.get(plat, [])
        for item in items:
            # 카테고리 필터링
            if category_pattern and not category_pattern.search(item.get("category", "")):
                continue
            
            # 검색어 필터링 (이름, 설명, 태그, 카테고리 대조)
            if query_pattern:
                searchable_text = f"{item.get('name', '')} {item.get('description', '')} {item.get('category', '')} {' '.join(item.get('tags', []))}"
                if not query_pattern.search(searchable_text):
                    continue

            # 플랫폼 명시 추가
            item_with_platform = dict(item)
            item_with_platform["platform"] = plat
            results.append(item_with_platform)

    if as_json:
        return json.dumps(results, ensure_ascii=False, indent=2)

    # 마크다운 포맷팅
    if not results:
        return f"❌ 검색 조건(Query: '{query or '전체'}', Platform: '{platform or '전체'}', Category: '{category or '전체'}')에 해당하는 개발자 자원을 찾을 수 없습니다."

    output = []
    output.append(f"# 🛠️ 개발자 자원 검색 결과 (총 {len(results)}건)\n")
    
    current_plat = None
    for res in results:
        if res["platform"] != current_plat:
            current_plat = res["platform"]
            output.append(f"## 🌐 Platform: `{current_plat}`\n")
        
        output.append(f"### 🔹 [{res['name']}]({res['url']})")
        output.append(f"- **카테고리**: `{res['category']}`")
        output.append(f"- **설명**: {res['description']}")
        
        if "free_tier" in res:
            output.append(f"- **무료 혜택**: {res['free_tier']}")
        if "auth" in res:
            output.append(f"- **인증 방식**: `{res['auth']}` (HTTPS: {res.get('https')}, CORS: {res.get('cors')})")
        
        tags_formatted = " ".join([f"`#{t}`" for t in res.get("tags", [])])
        output.append(f"- **태그**: {tags_formatted}\n")

    return "\n".join(output)


def list_summary() -> str:
    """전체 플랫폼 현황 요약 출력"""
    summary = ["# 📚 개발자 자원 및 트렌드 허브 (Developer Resources Hub)\n"]
    summary.append("사용 가능한 4대 전문 자원 수록 현황:\n")

    for plat, items in DEV_RESOURCES_DATA.items():
        summary.append(f"### 📌 `{plat}` ({len(items)}개 등록)")
        cats = sorted(list(set(item["category"] for item in items)))
        summary.append(f"- **주요 카테고리**: {', '.join(cats)}")
        sample_names = [item['name'] for item in items[:3]]
        summary.append(f"- **대표 항목**: {', '.join(sample_names)} 등\n")

    summary.append("\n💡 **사용 가이드:**")
    summary.append("- `python scripts/query_dev_resources.py --query postgres` (데이터베이스 관련 자원 검색)")
    summary.append("- `python scripts/query_dev_resources.py --platform free-for-dev` (무료 SaaS/인프라 전체)")
    summary.append("- `python scripts/query_dev_resources.py --platform public-apis.io` (공개 API 목록)")
    summary.append("- `python scripts/query_dev_resources.py --platform devresourc.es` (UI 컴포넌트/디자인/치트시트)")
    
    return "\n".join(summary)


def main():
    parser = argparse.ArgumentParser(description="개발자 자원 및 트렌드 허브 (Developer Resources Hub) 조회기")
    parser.add_argument("-q", "--query", help="검색 키워드 (예: postgres, auth, weather, tailwind)")
    parser.add_argument("-p", "--platform", choices=["free-for-dev", "public-apis.io", "daily-dev", "devresourc.es"], help="특정 플랫폼으로 필터링")
    parser.add_argument("-c", "--category", help="카테고리 필터링 (예: Hosting, Database, UI Components)")
    parser.add_argument("--json", action="store_true", help="JSON 데이터 구조로 출력")
    parser.add_argument("--summary", action="store_true", help="전체 카테고리 및 플랫폼 현황 요약 출력")

    args = parser.parse_args()

    if args.summary or (not args.query and not args.platform and not args.category and not args.json):
        print(list_summary())
    else:
        print(search_resources(query=args.query, platform=args.platform, category=args.category, as_json=args.json))


if __name__ == "__main__":
    main()
