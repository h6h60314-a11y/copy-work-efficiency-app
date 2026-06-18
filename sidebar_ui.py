from __future__ import annotations

from html import escape
from typing import Sequence

import streamlit as st

from nav_config import PageSpec, SectionSpec


BRAND_GREEN = "#1DA539"
SIDEBAR_SCALE = 1.22

# Change these numbers when you want to adjust each sidebar text level.
ROOT_TEXT_SIZE = 18
SECTION_TEXT_SIZE = 19
CHILD_TEXT_SIZE = 18

ROOT_ICON_SIZE = 23
SECTION_ICON_SIZE = 24
CHILD_ICON_SIZE = 23

BRAND_KICKER = "\u5927\u6a39\u91ab\u85e5\u80a1\u4efd\u6709\u9650\u516c\u53f8"
BRAND_TITLE = "\u5927\u8c50\u7269\u6d41\u90e8"
BRAND_SUBTITLE = "\u4f5c\u696d\u5e73\u53f0"
BRAND_IMAGE_DATA_URI = (
    "data:image/png;base64,"
    "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"
    "wn8BwvL/0LrqEbcAAAAASUVORK5CYII="
)


def _link(spec: PageSpec, label: str, css_class: str) -> str:
    icon = escape(spec.icon or "")
    text = escape(label)
    href = "/" + escape(spec.url_path.lstrip("/"))

    text_sizes = {
        "nav-root": ROOT_TEXT_SIZE,
        "nav-section": SECTION_TEXT_SIZE,
        "nav-child": CHILD_TEXT_SIZE,
    }
    icon_sizes = {
        "nav-root": ROOT_ICON_SIZE,
        "nav-section": SECTION_ICON_SIZE,
        "nav-child": CHILD_ICON_SIZE,
    }
    text_size = text_sizes.get(css_class, CHILD_TEXT_SIZE)
    icon_size = icon_sizes.get(css_class, CHILD_ICON_SIZE)
    text_style = f"font-size:{text_size}px!important;font-weight:inherit!important;"
    icon_style = f"font-size:{icon_size}px!important;width:{icon_size + 4}px!important;"

    return (
        f'<a class="nav-link {css_class}" href="{href}" target="_self">'
        f'<span class="nav-icon" style="{icon_style}">{icon}</span>'
        f'<span class="nav-text" style="{text_style}">{text}</span>'
        "</a>"
    )


def render_sidebar(page_sections: Sequence[SectionSpec]) -> None:
    css = [
        "<style>",
        f":root{{--brand-green:{BRAND_GREEN};--sidebar-scale:{SIDEBAR_SCALE};}}",
        "section[data-testid='stSidebar']{background:#f8fafc!important;border-right:1px solid rgba(15,23,42,.10)!important;}",
        "section[data-testid='stSidebar'] *{font-family:'Noto Sans TC','Microsoft JhengHei',Arial,sans-serif!important;}",
        "section[data-testid='stSidebar'] [data-testid='stSidebarContent']{padding:4px 26px 30px 26px!important;}",
        "section[data-testid='stSidebar'] div[data-testid='stMarkdown']{margin:0!important;}",
        ".sidebar-scale-shell{zoom:var(--sidebar-scale);padding-top:14px;}",
        ".brand-block{display:flex;align-items:center;gap:16px;margin:0 0 22px 0;padding:0;background:transparent;border:0;box-shadow:none;}",
        ".brand-logo{width:58px;height:58px;object-fit:contain;display:block;filter:drop-shadow(0 3px 4px rgba(29,165,57,.18));}",
        ".brand-text{display:flex;flex-direction:column;gap:6px;color:#0f172a;white-space:nowrap;}",
        ".brand-kicker{font-size:15px;font-weight:900;line-height:1.05;color:#334155;}",
        ".brand-title{font-size:25px;font-weight:950;line-height:1.05;color:#0f172a;letter-spacing:.3px;}",
        ".brand-subtitle{font-size:16px;font-weight:900;line-height:1.05;color:#334155;}",
        ".nav-list{display:flex;flex-direction:column;gap:0;}",
        ".nav-link{display:flex;align-items:center;text-decoration:none!important;color:#0f172a!important;border-radius:8px;line-height:1.22!important;}",
        ".nav-link:hover{background:rgba(29,165,57,.08);}",
        ".nav-root{gap:10px;margin:0 0 25px 0;padding:9px 14px;background:linear-gradient(180deg,#39B54A,#2F9E44)!important;color:#fff!important;box-shadow:0 8px 16px rgba(29,165,57,.22);}",
        ".nav-root .nav-text,.nav-root .nav-icon{color:#fff!important;}",
        ".nav-section{gap:10px;margin:23px 0 13px 0;padding:5px 0;font-weight:950!important;}",
        ".nav-child{gap:10px;margin:0 0 13px 30px;padding:5px 4px;font-weight:850!important;}",
        ".nav-root .nav-text{font-weight:900!important;}",
        ".nav-section .nav-text{font-weight:950!important;}",
        ".nav-child .nav-text{font-weight:850!important;}",
        ".nav-icon{display:inline-flex;justify-content:center;align-items:center;line-height:1;flex:0 0 auto;}",
        "</style>",
    ]

    links = [
        '<div class="sidebar-scale-shell">',
        f'<div class="brand-block" aria-label="{escape(BRAND_KICKER)} {escape(BRAND_TITLE)} {escape(BRAND_SUBTITLE)}">',
        f'<img class="brand-logo" src="{BRAND_IMAGE_DATA_URI}" alt="大樹圖示">',
        '<div class="brand-text">',
        f'<div class="brand-kicker">{escape(BRAND_KICKER)}</div>',
        f'<div class="brand-title">{escape(BRAND_TITLE)}</div>',
        f'<div class="brand-subtitle">{escape(BRAND_SUBTITLE)}</div>',
        "</div>",
        "</div>",
        '<div class="nav-list">',
    ]

    for section in page_sections:
        if not section.pages:
            continue
        if not section.title:
            links.extend(_link(spec, spec.title, "nav-root") for spec in section.pages)
            continue
        links.append(_link(section.pages[0], section.title, "nav-section"))
        links.extend(_link(spec, spec.title, "nav-child") for spec in section.pages[1:])

    links.extend(["</div>", "</div>"])
    st.sidebar.markdown("\n".join(css + links), unsafe_allow_html=True)
