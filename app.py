from __future__ import annotations

import ast
import json
from pathlib import Path

import streamlit as st

from nav_config import APP_ICON, APP_TITLE, PAGE_SECTIONS, PageSpec


st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
)

BROKEN_PAGES: list[tuple[str, str]] = []
MISSING_PAGES: list[str] = []
SECTION_HOME_URLS = {
    "planning-home",
    "outbound-home",
    "inbound-home",
    "gt-kpi-home",
    "df-kpi-home",
}


def _syntax_ok(path: Path) -> bool:
    try:
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        return True
    except Exception as exc:
        BROKEN_PAGES.append((str(path), repr(exc)))
        return False


def _page_from_spec(spec: PageSpec):
    path = Path(spec.path)
    if not path.exists():
        MISSING_PAGES.append(spec.path)
        return None
    if not _syntax_ok(path):
        return None

    kwargs = {
        "title": spec.title,
        "url_path": spec.url_path,
    }
    if spec.icon:
        kwargs["icon"] = spec.icon
    if spec.default:
        kwargs["default"] = True
    return st.Page(str(path), **kwargs)


def _show_preflight_warnings() -> None:
    if MISSING_PAGES:
        with st.sidebar.expander("缺少頁面檔案", expanded=False):
            st.caption("下列頁面設定找不到對應檔案，已暫時從導覽列排除。")
            for path in MISSING_PAGES:
                st.code(path)

    if BROKEN_PAGES:
        with st.sidebar.expander("頁面語法檢查失敗", expanded=True):
            st.caption("下列頁面有 SyntaxError / IndentationError，已暫時從導覽列排除。")
            for path, error in BROKEN_PAGES:
                st.code(f"{path}\n{error}")


def _section_home_links_script() -> str:
    mappings = []
    for section in PAGE_SECTIONS:
        if not section.title or not section.pages:
            continue
        first_page = section.pages[0]
        if first_page.url_path in SECTION_HOME_URLS:
            mappings.append({"label": section.title, "key": first_page.url_path})

    hidden_selectors = "\n".join(
        f'section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="{url_path}"])'
        "{ display:none !important; }"
        for url_path in sorted(SECTION_HOME_URLS)
    )

    return f"""
<style>
{hidden_selectors}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h2,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h3,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h4{{
  cursor: pointer;
  border-radius: 10px;
  padding: 6px 8px;
  margin-left: -8px;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h2:hover,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h3:hover,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h4:hover{{
  background: rgba(2,132,199,0.10);
