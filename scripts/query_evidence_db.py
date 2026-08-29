#!/usr/bin/env python3
"""query_evidence_db.py - 압수 SQLite DB 읽기전용 즉석 분석기 + 잔존 흔적 검색.

메신저 백업본·앱 데이터·브라우저 히스토리 같은 SQLite DB에서 SQL로 데이터를
추출하고, 삭제된 레코드가 페이지에 남긴 잔존 흔적을 키워드로 검색한다.

규율:
- **읽기전용 강제.** DB는 file:...?mode=ro 로 열고, SELECT/PRAGMA/EXPLAIN/WITH
  이외의 문은 실행을 거부한다. 증거 원본을 훼손하지 않는다.
- **흔적 검색은 복구가 아니다.** 잔존 스캔은 삭제된 레코드가 페이지에 남긴
  바이트를 찾을 뿐이며, VACUUM·secure_delete로 이미 지워졌으면 못 찾는다.
  "존재 증명"이 아니라 "부존재 증명도 아님" — 찾은 것만 보고한다.

Exit code: 0 완료 / 2 실행 오류 (파일 없음·금지된 문·SQLite 오류)
CLI:
    python scripts/query_evidence_db.py 증거.db --list-schema
    python scripts/query_evidence_db.py 증거.db --sql "SELECT * FROM messages LIMIT 50"
    python scripts/query_evidence_db.py 증거.db --keywords "회사명,010-1234-5678" -o 흔적.md
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sqlite3
import sys

# 원본 훼손 방지 — 이 네 가지로 시작하는 문만 허용한다.
_ALLOWED_PREFIXES = ("select", "pragma", "explain", "with")
_SQL_COMMENT_RE = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.DOTALL)
_ENCODINGS = ("utf-8", "utf-16-le", "utf-16-be")
_CONTEXT_BYTES = 60
_CELL_LIMIT = 80


def open_readonly(db_path: str) -> sqlite3.Connection:
    """증거 DB를 절대 쓰지 않는 모드로 연다. URI 상대경로 이스케이프 주의."""
    abs_path = os.path.abspath(db_path).replace("?", "%3f").replace("#", "%23")
    uri = f"file:{abs_path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def check_statement(sql: str) -> str:
    """단일 문장 + 화이트리스트 접두어 검사. 위반 시 ValueError."""
    cleaned = _SQL_COMMENT_RE.sub(" ", sql).strip().rstrip(";").strip()
    if not cleaned:
        raise ValueError("빈 SQL 문입니다")
    first = cleaned.split(None, 1)[0].lower()
    if first not in _ALLOWED_PREFIXES:
        raise ValueError(
            f"금지된 문입니다: {first.upper()} — 읽기전용 증거 DB에는 "
            f"SELECT/PRAGMA/EXPLAIN/WITH만 허용됩니다"
        )
    return cleaned


def run_query(conn: sqlite3.Connection, sql: str, limit: int) -> tuple[list[str], list[list]]:
    cur = conn.execute(check_statement(sql))
    columns = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchmany(limit)
    return columns, [list(r) for r in rows]


def list_schema(conn: sqlite3.Connection) -> list[dict]:
    tables = [
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    out: list[dict] = []
    for table in tables:
        cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        out.append({
            "table": table,
            "columns": [(c[1], c[2]) for c in cols],
            "rows": count,
        })
    return out


def _printable_context(raw: bytes, start: int, length: int) -> str:
    lo = max(0, start - _CONTEXT_BYTES)
    hi = min(len(raw), start + length + _CONTEXT_BYTES)
    chunk = raw[lo:hi]
    text = chunk.decode("utf-8", errors="replace")
    text = "".join(ch if ch.isprintable() or ch in "\n\t" else "·" for ch in text)
    return text.replace("\n", " ")


def scan_residual(db_path: str, keywords: list[str]) -> list[dict]:
    """파일 원시 바이트에서 키워드 잔존 흔적을 검색한다.

    본 파일과 -wal·-journal 동반 파일을 모두 본다. 삭제된 레코드가 아직
    재사용되지 않은 페이지에 남아 있으면 발견된다.
    """
    siblings = [db_path]
    for suffix in ("-wal", "-journal"):
        if os.path.exists(db_path + suffix):
            siblings.append(db_path + suffix)

    hits: list[dict] = []
    seen: set[tuple] = set()
    for path in siblings:
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as exc:
            print(f"[WARN] 읽기 실패 {path}: {exc}", file=sys.stderr)
            continue
        for keyword in keywords:
            for enc in _ENCODINGS:
                needle = keyword.encode(enc, errors="ignore")
                if not needle:
                    continue
                start = 0
                while True:
                    idx = raw.find(needle, start)
                    if idx < 0:
                        break
                    key = (path, keyword, idx, enc)
                    if key not in seen:
                        seen.add(key)
                        hits.append({
                            "file": os.path.basename(path) + (f" ({suffix.strip('-')})" if suffix and path.endswith(suffix) else ""),
                            "keyword": keyword,
                            "encoding": enc,
                            "offset": idx,
                            "context": _printable_context(raw, idx, len(needle)),
                        })
                    start = idx + 1
    hits.sort(key=lambda h: (h["file"], h["keyword"], h["offset"]))
    return hits


def rows_to_markdown(columns: list[str], rows: list[list]) -> str:
    def cell(v) -> str:
        s = str(v) if v is not None else "(NULL)"
        s = s.replace("|", "\\|").replace("\n", " ")
        return s[:_CELL_LIMIT] + ("…" if len(s) > _CELL_LIMIT else "")

    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(lines)


def rows_to_csv(columns: list[str], rows: list[list]) -> str:
    import io
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([str(v) if v is not None else "" for v in row])
    return buf.getvalue()


def render_report(schema: list[dict], query_block: str, hits: list[dict]) -> str:
    lines = ["# SQLite 증거 DB 분석 보고서\n"]

    if schema:
        lines.append("## 스키마\n")
        lines.append("| 테이블 | 행 수 | 열 |")
        lines.append("| :-- | ---: | :-- |")
        for t in schema:
            cols = ", ".join(f"{name}({typ})" for name, typ in t["columns"])
            lines.append(f"| {t['table']} | {t['rows']:,} | {cols} |")
        lines.append("")

    if query_block:
        lines.append("## 쿼리 결과\n")
        if query_block.startswith("```"):
            lines.append(query_block)  # 이미 펜스가 쳐진 기계 판독 형식
        else:
            lines.append(query_block)
        lines.append("")

    lines.append("## 잔존 흔적 검색 (삭제 레코드 잔존 바이트)\n")
    if hits:
        lines.append("| 파일 | 키워드 | 인코딩 | 오프셋 | 주변 내용 |")
        lines.append("| :-- | :-- | :-- | ---: | :-- |")
        for h in hits:
            lines.append(
                f"| {h['file']} | {h['keyword']} | {h['encoding']} | {h['offset']:,} | `{h['context']}` |"
            )
        lines.append(
            "\n> 잔존 흔적은 삭제된 데이터가 페이지에 남아 있음을 보여주는 참고 정보입니다. "
            "복구 보장이 아니며, VACUUM·secure_delete 이후에는 발견되지 않습니다. "
            "존재의 법적 의미는 포렌식 전문가 검토가 필요합니다."
        )
    else:
        lines.append("발견된 흔적 없음. (부존재의 증명이 아니다 — VACUUM 등으로 이미 덮였을 수 있습니다)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="압수 SQLite DB 읽기전용 쿼리 + 잔존 흔적 검색")
    p.add_argument("db", help="SQLite DB 파일 경로")
    p.add_argument("--sql", default="", help="실행할 SELECT 문 (읽기전용 강제)")
    p.add_argument("--list-schema", action="store_true", help="테이블·열·행 수 나열")
    p.add_argument("--keywords", default="", help="쉼표 구분 잔존 흔적 키워드")
    p.add_argument("--format", choices=("md", "csv"), default="md", help="쿼리 결과 출력 형식 (기본 md)")
    p.add_argument("--limit", type=int, default=1000, help="쿼리 최대 행 수 (기본 1000)")
    p.add_argument("--output", "-o", default="", help="보고서 저장 경로 (미지정 시 stdout)")
    args = p.parse_args(argv)

    if not os.path.isfile(args.db):
        print(f"error: DB 파일을 찾을 수 없습니다: {args.db}", file=sys.stderr)
        return 2
    if not (args.sql or args.list_schema or args.keywords):
        print("error: --sql, --list-schema, --keywords 중 하나는 지정해야 합니다.", file=sys.stderr)
        return 2

    try:
        conn = open_readonly(args.db)
    except sqlite3.Error as exc:
        print(f"error: DB를 열지 못했습니다: {exc}", file=sys.stderr)
        return 2

    try:
        schema: list[dict] = []
        query_block = ""
        if args.list_schema:
            schema = list_schema(conn)
        if args.sql:
            columns, rows = run_query(conn, args.sql, args.limit)
            if args.format == "csv":
                # 기계 판독용 블록 — 보고서 안에서 ```csv 펜스로 추출 가능하게
                query_block = "```csv\n" + rows_to_csv(columns, rows) + "```"
            else:
                query_block = rows_to_markdown(columns, rows)
    except (ValueError, sqlite3.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        conn.close()
        return 2
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    hits = scan_residual(args.db, keywords) if keywords else []

    report = render_report(schema, query_block, hits)
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[OK] 분석 보고서 저장: {args.output}")
    else:
        print(report)
    return 0


# ── 콘솔 하드닝 (#84) ───────────────────────────────────────────────
import os as _os  # noqa: E402
import sys as _sys  # noqa: E402

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import console as _console  # noqa: E402

if __name__ == "__main__":
    _console.force_utf8_console()
    raise SystemExit(main())
