from __future__ import annotations

import ast
from dataclasses import replace
from html import escape
from pathlib import Path

import streamlit as st

from nav_config import APP_ICON, APP_TITLE, PAGE_SECTIONS, PageSpec


st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

BROKEN_PAGES: list[tuple[str, str]] = []
MISSING_PAGES: list[str] = []


def syntax_ok(path: Path) -> bool:
    try:
        ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        return True
    except Exception as exc:
        BROKEN_PAGES.append((str(path), repr(exc)))
        return False


def make_page(spec: PageSpec):
    path = Path(spec.path)
    if not path.exists():
        MISSING_PAGES.append(spec.path)
        return None
    if not syntax_ok(path):
        return None

    kwargs = {"title": spec.title, "url_path": spec.url_path}
    if spec.icon:
        kwargs["icon"] = spec.icon
    if spec.default:
        kwargs["default"] = True
    return st.Page(str(path), **kwargs)


def all_pages():
    result = []
    for section in PAGE_SECTIONS:
        for index, spec in enumerate(section.pages):
            item = replace(spec, title=section.title) if section.title and index == 0 else spec
            page = make_page(item)
            if page:
                result.append(page)
    return result


def sidebar_link(spec: PageSpec, label: str, css_class: str) -> str:
    icon = escape(spec.icon or "")
    text = escape(label)
    href = "/" + escape(spec.url_path.lstrip("/"))
    if css_class == "nav-section":
        link_style = "font-size:20px!important;font-weight:950!important;margin:23px 0 11px 0;padding:5px 0;color:#0f172a;"
        text_style = "font-size:20px!important;font-weight:950!important;"
        icon_style = "font-size:25px!important;width:27px;flex:0 0 27px;"
    elif css_class == "nav-child":
        link_style = "font-size:16px!important;font-weight:850!important;margin:0 0 11px 28px;padding:5px 6px;color:#0f172a;"
        text_style = "font-size:16px!important;font-weight:850!important;"
        icon_style = "font-size:20px!important;width:22px;flex:0 0 22px;"
    else:
        link_style = "font-size:17px!important;font-weight:850!important;margin:0 0 23px 0;padding:6px 6px;color:#0f172a;"
        text_style = "font-size:17px!important;font-weight:850!important;"
        icon_style = "font-size:21px!important;width:23px;flex:0 0 23px;"

    return (
        f'<a class="nav-link {css_class}" style="{link_style}" href="{href}" target="_self">'
        f'<span class="nav-icon" style="{icon_style}">{icon}</span>'
        f'<span class="nav-text" style="{text_style}">{text}</span>'
        f"</a>"
    )


def render_sidebar() -> None:
    css = [
        "<style>",
        "section[data-testid='stSidebar']{background:#f8fafc!important;border-right:1px solid rgba(15,23,42,.10)!important;}",
        "section[data-testid='stSidebar'] *{font-family:'Noto Sans TC','Microsoft JhengHei',system-ui,sans-serif;}",
        "section[data-testid='stSidebar'] [data-testid='stSidebarContent']{padding:18px 18px 24px 18px!important;}",
        "section[data-testid='stSidebar'] div[data-testid='stMarkdown']{margin:0!important;}",
        ".nav-link{display:flex;align-items:center;gap:10px;text-decoration:none!important;color:#0f172a!important;border-radius:7px;line-height:1.28!important;}",
        ".nav-link:hover{background:rgba(2,132,199,.08);}",
        ".nav-icon{display:inline-flex;justify-content:center;align-items:center;line-height:1;}",
        ".nav-root{font-size:17px!important;font-weight:850!important;margin:0 0 23px 0;padding:6px 6px;}",
        ".nav-section{font-size:20px!important;font-weight:950!important;margin:23px 0 11px 0;padding:5px 0;color:#0f172a!important;}",
        ".nav-child{font-size:16px!important;font-weight:850!important;margin:0 0 11px 28px;padding:5px 6px;}",
        ".nav-child .nav-text{font-size:16px!important;font-weight:850!important;}",
        ".nav-section .nav-text{font-size:20px!important;font-weight:950!important;}",
        ".nav-root .nav-text{font-size:17px!important;font-weight:850!important;}",
        "</style>",
    ]

    links = []
    for section in PAGE_SECTIONS:
        if not section.pages:
            continue
        if not section.title:
            links.extend(sidebar_link(spec, spec.title, "nav-root") for spec in section.pages)
            continue

        links.append(sidebar_link(section.pages[0], section.title, "nav-section"))
        links.extend(sidebar_link(spec, spec.title, "nav-child") for spec in section.pages[1:])

    st.sidebar.markdown("\n".join(css + links), unsafe_allow_html=True)


pg = st.navigation(all_pages(), position="hidden")
render_sidebar()
pg.run()
