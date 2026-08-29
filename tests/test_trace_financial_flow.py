"""trace_financial_flow.py 회귀 테스트 — 집계·순환 감지·홉·한계 처리."""

import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import trace_financial_flow as tff  # noqa: E402

CSV_HEADER = "거래일시,입금액,출금액,상대방"


@pytest.fixture()
def stmt_csv(tmp_path):
    # 열 순서: 거래일시, 입금액, 출금액, 상대방
    rows = [
        CSV_HEADER,
        # 홉: B에서 입금 → 다음 날 C로 출금 (7일 창 내)
        "2026-08-01,5000000,,B카페",
        "2026-08-02,,3000000,C전자",
        # 순환: A에 출금 후 3일 뒤 A에서 재입금
        "2026-08-03,,1000000,A개인",
        "2026-08-06,1000000,,A개인",
        # 창 밖(19일) 순환 → 감지되면 안 됨
        "2026-08-01,,7000000,D상사",
        "2026-08-20,7000000,,D상사",
        # 소액 노이즈
        "2026-08-10,100,,서비스업체",
    ]
    p = tmp_path / "거래내역.csv"
    p.write_text("\n".join(rows), encoding="utf-8")
    return p


def test_normalize_columns_and_amounts(stmt_csv):
    columns, rows = tff.read_rows(str(stmt_csv))
    records = tff.normalize(columns, rows)
    kinds = [(r["counterparty"], r["kind"], r["amount"]) for r in records]
    assert ("B카페", "입금", 5_000_000) in kinds
    assert ("C전자", "출금", -3_000_000) in kinds
    assert ("A개인", "출금", -1_000_000) in kinds


def test_summarize_ranking_by_volume(stmt_csv):
    columns, rows = tff.read_rows(str(stmt_csv))
    records = tff.normalize(columns, rows)
    summary = tff.summarize(records)
    top_cp = summary["ranking"][0][0]
    assert top_cp == "D상사"  # 입출 합 1400만으로 최대
    assert summary["total_in"] == 13_000_100
    assert summary["total_out"] == 11_000_000


def test_round_trip_within_window_only(stmt_csv):
    columns, rows = tff.read_rows(str(stmt_csv))
    records = tff.normalize(columns, rows)
    trips = tff.detect_round_trips(records, window_days=7)
    cps = {t["counterparty"] for t in trips}
    assert "A개인" in cps        # 3일 만에 재입금 → 감지
    assert "D상사" not in cps    # 19일 간격 → 창 밖


def test_hops_in_to_out(stmt_csv):
    columns, rows = tff.read_rows(str(stmt_csv))
    records = tff.normalize(columns, rows)
    hops = tff.detect_hops(records, window_days=7)
    pairs = {(h["from"], h["to"]) for h in hops}
    assert ("B카페", "C전자") in pairs
    assert ("B카페", "A개인") in pairs  # 2일 간격 홉


def test_mermaid_and_markdown_render(stmt_csv):
    columns, rows = tff.read_rows(str(stmt_csv))
    records = tff.normalize(columns, rows)
    summary = tff.summarize(records)
    md = tff.render_markdown(records, summary, [], [], 7, 20)
    assert "```mermaid" in md and "flowchart" in md
    assert "자금 순환 의심" in md
    assert "단일 계좌 명세 기반" in md  # 한계 고지


def test_amount_plus_direction_columns(tmp_path):
    p = tmp_path / "gubun.csv"
    p.write_text(
        "거래일,금액,구분,내용\n2026-08-01,100000,입금,급여\n2026-08-02,30000,출금,이체\n",
        encoding="utf-8",
    )
    columns, rows = tff.read_rows(str(p))
    records = tff.normalize(columns, rows)
    assert {r["kind"] for r in records} == {"입금", "출금"}


def test_missing_columns_exit_2(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("아무열,다른열\n1,2\n", encoding="utf-8")
    assert tff.main([str(p)]) == 2
    assert tff.main([str(tmp_path / "없음.csv")]) == 2


def test_fake_xlsx_graceful_error(tmp_path):
    """openpyxl로도 못 읽는 위조 xlsx는 트레이스백 대신 exit 2."""
    p = tmp_path / "거래.xlsx"
    p.write_bytes(b"not a real xlsx")
    # openpyxl이 설치된 환경: ValueError → exit 2. 미설치면 openpyxl 안내 ValueError → exit 2.
    assert tff.main([str(p)]) == 2
