from __future__ import annotations

import ast
from dataclasses import replace
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

    kwargs = {"title": spec.title, "url_path": spec.url_path}
    if spec.icon:
        kwargs["icon"] = spec.icon
    if spec.default:
        kwargs["default"] = True

    return st.Page(str(path), **kwargs)


def _navigation_pages():
    pages = []
    for section in PAGE_SECTIONS:
        for index, spec in enumerate(section.pages):
            page_spec = spec
            if section.title and index == 0:
                page_spec = replace(spec, title=section.title)

            page = _page_from_spec(page_spec)
            if page:
                pages.append(page)
    return pages


def _sidebar_css() -> None:
    css = "\n".join(
        [
            "<style>",
            "section[data-testid='stSidebar']{background:#0f2135!important;border-right:0!important;}",
            "section[data-testid='stSidebar'] *{font-family:'Noto Sans TC','Microsoft JhengHei',system-ui,sans-serif;}",
            "section[data-testid='stSidebar'] [data-testid='stSidebarContent']{padding-top:12px;}",
            "section[data-testid='stSidebar'] a[data-testid='stPageLink']{text-decoration:none!important;color:#eef6ff!important;}",
            "section[data-testid='stSidebar'] div[data-testid='stPageLink']{margin:0!important;}",
            "section[data-testid='stSidebar'] div[data-testid='stPageLink'] a{border-radius:8px!important;min-height:36px!important;}",
            "section[data-testid='stSidebar'] div[data-testid='stPageLink'] a:hover{background:rgba(255,255,255,.08)!important;}",
            "section[data-testid='stSidebar'] div[data-testid='stPageLink'] a[aria-current='page']{background:rgba(90,160,230,.22)!important;}",
            "section[data-testid='stSidebar'] div[data-testid='stPageLink'] span{color:#eef6ff!important;}",
            ".nav-root{margin:0 0 14px 0;}",
            ".nav-root div[data-testid='stPageLink'] a{font-weight:850!important;font-size:15px!important;padding:7px 10px!important;}",
            ".nav-section{margin:18px 0 8px 0;}",
            ".nav-section div[data-testid='stPageLink'] a{font-weight:850!important;font-size:14px!important;color:#cde4fb!important;padding:4px 2px!important;background:transparent!important;}",
            ".nav-section div[data-testid='stPageLink'] a:hover{background:rgba(255,255,255,.06)!important;}",
            ".nav-child{margin-left:24px;margin-bottom:8px;}",
            ".nav-child div[data-testid='stPageLink'] a{font-weight:950!important;font-size:17px!important;line-height:1.35!important;padding:7px 10px!important;}",
            ".nav-child div[data-testid='stPageLink'] span{font-weight:950!important;}",
            ".nav-child svg,.nav-section svg,.nav-root svg{filter:drop-shadow(0 1px 0 rgba(0,0,0,.18));}",
            "section[data-testid='stSidebar'] button[kind='header']{color:#eef6ff!important;}",
            "</style>",
        ]
    )
    st.markdown(css, unsafe_allow_html=True)


def _sidebar_page_link(spec: PageSpec, *, label: str, css_class: str) -> None:
    st.sidebar.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
    try:
        st.sidebar.page_link(spec.path, label=label, icon=spec.icon or None)
    except Exception:
        st.sidebar.markdown(label)
    st.sidebar.markdown("</div>", unsafe_allow_html=True)


def _render_sidebar_navigation() -> None:
