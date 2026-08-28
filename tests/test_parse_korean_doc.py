"""parse_korean_doc.py 회귀 테스트 — 실제 HWPX(OWPML) 표준 네임스페이스 기반."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "parse_korean_doc.py"

# 실제 HWPX(OWPML/KS X 6101)가 사용하는 표준 네임스페이스
HP_NS = "http://www.hancom.co.kr/hwpml/2011/hp"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/hs"

SECTION_TMPL = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hs:root xmlns:hs="{hs}" xmlns:hp="{hp}">
  <hp:body>
    <hp:p><hp:t>제{{i}}조 표준 네임스페이스 문단입니다.</hp:t></hp:p>
    <hp:tbl>
      <hp:tr><hp:tc><hp:t>항목</hp:t></hp:tc><hp:tc><hp:t>금액</hp:t></hp:tc></hp:tr>
      <hp:tr><hp:tc><hp:t>계약금</hp:t></hp:tc><hp:tc><hp:t>{{i}}000원</hp:t></hp:tc></hp:tr>
    </hp:tbl>
  </hp:body>
</hs:root>
""".format(hs=HS_NS, hp=HP_NS)

CONTENT_HPF = """<?xml version="1.0" encoding="UTF-8"?>
<pkg:package xmlns:pkg="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>표준 계약서</dc:title>
  <dc:creator>홍길동</dc:creator>
</pkg:package>
"""


def _build_hwpx(path: Path, section_count: int = 1) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Contents/content.hpf", CONTENT_HPF)
        for i in range(section_count):
            z.writestr(f"Contents/section{i}.xml", SECTION_TMPL.replace("{i}", str(i)))
    return path


def _run(path: Path, *extra: str) -> dict:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), *extra],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_hwpx_standard_namespace_text_extraction(tmp_path):
    """회귀: 표준 hwpml/2011/hp 네임스페이스 HWPX에서 텍스트가 추출되어야 한다."""
    hwpx = _build_hwpx(tmp_path / "real.hwpx")
    out = _run(hwpx)
    assert "표준 네임스페이스 문단입니다" in out["text"]
    assert out["metadata"].get("title") == "표준 계약서"
    assert out["metadata"].get("creator") == "홍길동"


def test_hwpx_table_extraction(tmp_path):
    hwpx = _build_hwpx(tmp_path / "table.hwpx")
    out = _run(hwpx)
    assert out["tables"], "표가 추출되어야 함"
    assert out["tables"][0][0] == ["항목", "금액"]


def test_hwpx_section_natural_sort(tmp_path):
    """section10.xml이 section2.xml보다 앞에 오지 않아야 한다."""
    hwpx = _build_hwpx(tmp_path / "multi.hwpx", section_count=11)
    out = _run(hwpx)
    names = [s["name"] for s in out["sections"]]
    assert names.index("Contents/section2.xml") < names.index("Contents/section10.xml")


def test_hwpx_markdown_output(tmp_path):
    hwpx = _build_hwpx(tmp_path / "md.hwpx")
    out_path = tmp_path / "parsed.md"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(hwpx), "--markdown", "--output", str(out_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    md = out_path.read_text(encoding="utf-8")
    assert "표준 네임스페이스 문단입니다" in md
    assert "| 항목 | 금액 |" in md


def test_legacy_hwpx_namespace_still_works(tmp_path):
    """구 네임스페이스(schemas.hancom.co.kr/owl) 문서도 하위 호환으로 파싱되어야 한다."""
    legacy = SECTION_TMPL.replace(HP_NS, "http://schemas.hancom.co.kr/owl/hp")
    path = tmp_path / "legacy.hwpx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Contents/section0.xml", legacy)
    out = _run(path)
    assert "표준 네임스페이스 문단입니다" in out["text"]


def test_hwp_invalid_file_returns_error_dict(tmp_path):
    """hwp-hwpx-parser가 설치되어 있어도 잘못된 .hwp는 크래시 없이 error dict를 반환한다."""
    bad = tmp_path / "bad.hwp"
    bad.write_bytes(b"not-an-hwp-file")
    r = subprocess.run([sys.executable, str(SCRIPT), str(bad)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "Error" in r.stderr
