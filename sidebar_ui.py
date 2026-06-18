from __future__ import annotations

from html import escape
from typing import Sequence

import streamlit as st

from nav_config import PageSpec, SectionSpec


def _link(spec: PageSpec, label: str, css_class: str) -> str:
    icon = escape(spec.icon or "")
    text = escape(label)
    href = "/" + escape(spec.url_path.lstrip("/"))

    styles = {
        "nav-section": (
            "font-size:28px!important;font-weight:950!important;margin:28px 0 16px 0;"
            "padding:6px 0;color:#0f172a;"
        ),
        "nav-child": (
            "font-size:22px!important;font-weight:850!important;margin:0 0 15px 34px;"
            "padding:6px 6px;color:#0f172a;"
        ),
        "nav-root": (
            "font-size:24px!important;font-weight:850!important;margin:0 0 28px 0;"
            "padding:8px 8px;color:#0f172a;"
        ),
    }
    text_sizes = {"nav-section": 28, "nav-child": 22, "nav-root": 24}
    icon_sizes = {"nav-section": 34, "nav-child": 28, "nav-root": 30}

    text_size = text_sizes.get(css_class, 16)
    icon_size = icon_sizes.get(css_class, 20)
    link_style = styles.get(css_class, styles["nav-child"])
    text_style = f"font-size:{text_size}px!important;font-weight:inherit!important;"
    icon_style = f"font-size:{icon_size}px!important;width:{icon_size + 2}px;flex:0 0 {icon_size + 2}px;"

    return (
        f'<a class="nav-link {css_class}" style="{link_style}" href="{href}" target="_self">'
        f'<span class="nav-icon" style="{icon_style}">{icon}</span>'
        f'<span class="nav-text" style="{text_style}">{text}</span>'
        "</a>"
    )


def render_sidebar(page_sections: Sequence[SectionSpec]) -> None:
    css = [
        "<style>",
        "section[data-testid='stSidebar']{background:#f8fafc!important;border-right:1px solid rgba(15,23,42,.10)!important;}",
        "section[data-testid='stSidebar'] *{font-family:'Noto Sans TC','Microsoft JhengHei',system-ui,sans-serif;}",
        "section[data-testid='stSidebar'] [data-testid='stSidebarContent']{padding:8px 22px 28px 22px!important;}",
        "section[data-testid='stSidebar'] div[data-testid='stMarkdown']{margin:0!important;}",
        ".brand-block{display:flex;align-items:center;justify-content:center;gap:18px;margin:-2px 0 24px 0;padding:10px 4px 14px 4px;border:0;background:transparent;box-shadow:none;}",
        ".brand-icon{font-size:64px;line-height:1;color:#1DA539;flex:0 0 64px;filter:drop-shadow(0 2px 2px rgba(29,165,57,.18));}",
        ".brand-kicker{font-size:20px;font-weight:900;line-height:1.1;color:#334155;letter-spacing:.2px;text-align:left;}",
        ".brand-title{font-size:46px;font-weight:950;line-height:1.02;color:#0f172a;letter-spacing:.6px;margin-top:6px;text-align:left;}",
        ".brand-subtitle{font-size:22px;font-weight:900;line-height:1.1;color:#334155;margin-top:7px;letter-spacing:.2px;text-align:left;}",
        ".brand-version{font-size:12px;font-weight:900;color:#1DA539;margin-top:6px;letter-spacing:.4px;}",
        ".nav-link{display:flex;align-items:center;gap:10px;text-decoration:none!important;color:#0f172a!important;border-radius:7px;line-height:1.28!important;}",
        ".nav-link:hover{background:rgba(29,165,57,.08);}",
        ".nav-root{background:linear-gradient(180deg,#39B54A,#2F9E44)!important;color:#fff!important;border-radius:8px!important;box-shadow:0 8px 16px rgba(29,165,57,.22);}",
        ".nav-root .nav-text,.nav-root .nav-icon{color:#fff!important;}",
        ".nav-icon{display:inline-flex;justify-content:center;align-items:center;line-height:1;}",
        "</style>",
    ]

    links = [
        '<div style="margin:-4px 0 22px 0;padding:4px 0 10px 0;">'
        '<svg width="285" height="118" viewBox="0 0 285 118" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="大樹醫藥體系 大豐物流 作業平台">'
        '<g transform="translate(18 24)">'
        '<circle cx="23" cy="17" r="13" fill="#1DA539"/>'
        '<circle cx="12" cy="30" r="12" fill="#1DA539"/>'
        '<circle cx="34" cy="31" r="12" fill="#1DA539"/>'
        '<rect x="19" y="28" width="9" height="27" rx="3" fill="#1DA539"/>'
        '</g>'
        '<text x="76" y="30" font-family="Noto Sans TC, Microsoft JhengHei, Arial, sans-serif" font-size="15" font-weight="900" fill="#334155">大樹醫藥體系</text>'
        '<text x="76" y="66" font-family="Noto Sans TC, Microsoft JhengHei, Arial, sans-serif" font-size="34" font-weight="900" fill="#0f172a">大豐物流</text>'
        '<text x="76" y="94" font-family="Noto Sans TC, Microsoft JhengHei, Arial, sans-serif" font-size="17" font-weight="900" fill="#334155">作業平台</text>'
        '<rect x="16" y="108" width="252" height="5" rx="2.5" fill="#1DA539"/>'
        '</svg>'
        "</div>"
    ]

    for section in page_sections:
        if not section.pages:
            continue
        if not section.title:
            links.extend(_link(spec, spec.title, "nav-root") for spec in section.pages)
            continue
        links.append(_link(section.pages[0], section.title, "nav-section"))
        links.extend(_link(spec, spec.title, "nav-child") for spec in section.pages[1:])

    st.sidebar.markdown("\n".join(css + links), unsafe_allow_html=True)
