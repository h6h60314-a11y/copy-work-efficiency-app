from __future__ import annotations

from html import escape
from typing import Sequence

import streamlit as st

from nav_config import PageSpec, SectionSpec


BRAND_GREEN = "#1DA539"
SIDEBAR_SCALE = 0.9


def _link(spec: PageSpec, label: str, css_class: str) -> str:
    icon = escape(spec.icon or "")
    text = escape(label)
    href = "/" + escape(spec.url_path.lstrip("/"))

    return (
        f'<a class="nav-link {css_class}" href="{href}" target="_self">'
        f'<span class="nav-icon">{icon}</span>'
        f'<span class="nav-text">{text}</span>'
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
        ".brand-icon{font-size:56px;line-height:1;color:var(--brand-green);filter:drop-shadow(0 3px 4px rgba(29,165,57,.18));}",
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
        ".nav-root .nav-text{font-size:18px!important;font-weight:900!important;}",
        ".nav-section .nav-text{font-size:19px!important;font-weight:950!important;}",
        ".nav-child .nav-text{font-size:16px!important;font-weight:850!important;}",
        ".nav-root .nav-icon{font-size:23px!important;width:27px;}",
        ".nav-section .nav-icon{font-size:24px!important;width:28px;}",
        ".nav-child .nav-icon{font-size:21px!important;width:25px;}",
        ".nav-icon{display:inline-flex;justify-content:center;align-items:center;line-height:1;flex:0 0 auto;}",
        "</style>",
    ]

    links = [
        '<div class="sidebar-scale-shell">',
        '<div class="brand-block" aria-label="大樹醫藥體系 大豐物流 作業平台">',
        '<div class="brand-icon">♣</div>',
        '<div class="brand-text">',
        '<div class="brand-kicker">大樹醫藥體系</div>',
        '<div class="brand-title">大豐物流</div>',
        '<div class="brand-subtitle">作業平台</div>',
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
