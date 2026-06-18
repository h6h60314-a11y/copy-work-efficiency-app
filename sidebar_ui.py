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
            "font-size:20px!important;font-weight:950!important;margin:23px 0 11px 0;"
            "padding:5px 0;color:#0f172a;"
        ),
        "nav-child": (
            "font-size:16px!important;font-weight:850!important;margin:0 0 11px 28px;"
            "padding:5px 6px;color:#0f172a;"
        ),
        "nav-root": (
            "font-size:17px!important;font-weight:850!important;margin:0 0 23px 0;"
            "padding:6px 6px;color:#0f172a;"
        ),
    }
    text_sizes = {"nav-section": 20, "nav-child": 16, "nav-root": 17}
    icon_sizes = {"nav-section": 25, "nav-child": 20, "nav-root": 21}

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
        "section[data-testid='stSidebar'] [data-testid='stSidebarContent']{padding:18px 18px 24px 18px!important;}",
        "section[data-testid='stSidebar'] div[data-testid='stMarkdown']{margin:0!important;}",
        ".brand-block{display:flex;align-items:center;gap:14px;margin:0 0 24px 0;padding:14px 12px 15px;border:1px solid rgba(29,165,57,.18);border-radius:14px;background:linear-gradient(135deg,#F1FBF3,#fff);box-shadow:0 10px 24px rgba(29,165,57,.08);}",
        ".brand-icon{font-size:44px;line-height:1;color:#3DBD57;flex:0 0 44px;filter:drop-shadow(0 2px 2px rgba(29,165,57,.18));}",
        ".brand-kicker{font-size:14px;font-weight:900;line-height:1.1;color:#334155;letter-spacing:.3px;}",
        ".brand-title{font-size:31px;font-weight:950;line-height:1.02;color:#0f172a;letter-spacing:.8px;margin-top:5px;}",
        ".brand-subtitle{font-size:16px;font-weight:900;line-height:1.1;color:#1f2937;margin-top:6px;letter-spacing:.4px;}",
        ".nav-link{display:flex;align-items:center;gap:10px;text-decoration:none!important;color:#0f172a!important;border-radius:7px;line-height:1.28!important;}",
        ".nav-link:hover{background:rgba(2,132,199,.08);}",
        ".nav-icon{display:inline-flex;justify-content:center;align-items:center;line-height:1;}",
        "</style>",
    ]

    links = [
        '<div class="brand-block"><div class="brand-icon">🌳</div><div>'
        '<div class="brand-kicker">大樹醫藥體系</div>'
        '<div class="brand-title">大豐物流</div>'
        '<div class="brand-subtitle">作業平台</div>'
        "</div></div>"
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
