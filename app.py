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

SECTION_HOME_URLS = {
    "planning-home",
    "outbound-home",
    "inbound-home",
    "gt-kpi-home",
    "df-kpi-home",
}

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


def _show_preflight_warnings() -> None:
    if MISSING_PAGES:
        with st.sidebar.expander("Missing page files", expanded=False):
            st.caption("These configured pages were not found and are excluded from navigation.")
            for path in MISSING_PAGES:
                st.code(path)

    if BROKEN_PAGES:
        with st.sidebar.expander("Page syntax errors", expanded=True):
            st.caption("These pages have syntax errors and are excluded from navigation.")
            for path, error in BROKEN_PAGES:
                st.code(f"{path}\n{error}")


def _section_home_mappings() -> list[dict[str, str]]:
    mappings: list[dict[str, str]] = []
    for section in PAGE_SECTIONS:
        if not section.title or not section.pages:
            continue
        first_page = section.pages[0]
        if first_page.url_path in SECTION_HOME_URLS:
            mappings.append({"label": section.title, "key": first_page.url_path})
    return mappings


def _sidebar_home_behavior() -> None:
    hide_rules = []
    for url_path in sorted(SECTION_HOME_URLS):
        selector = (
            'section[data-testid="stSidebar"] '
            f'li:has(a[data-testid="stSidebarNavLink"][href*="{url_path}"])'
        )
        hide_rules.append(f"{selector}{{display:none!important;}}")

    css_lines = [
        "<style>",
        *hide_rules,
        'section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h2,',
        'section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h3,',
        'section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h4{',
        "cursor:pointer;border-radius:10px;padding:6px 8px;margin-left:-8px;",
        "}",
        'section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h2:hover,',
        'section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h3:hover,',
        'section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h4:hover{',
        "background:rgba(2,132,199,0.10);",
        "}",
        "</style>",
    ]

    mappings_json = json.dumps(_section_home_mappings(), ensure_ascii=False)
    js_lines = [
        "<script>",
        "(function(){",
        f"const SECTION_HOMES={mappings_json};",
        "function bindSectionHomes(){",
        "const sidebar=document.querySelector('section[data-testid=\"stSidebar\"]');",
        "if(!sidebar)return;",
        "const homeHrefs={};",
        "sidebar.querySelectorAll('a[data-testid=\"stSidebarNavLink\"]').forEach(a=>{",
        "const href=a.getAttribute('href')||a.href||'';",
        "SECTION_HOMES.forEach(item=>{if(href.includes(item.key))homeHrefs[item.key]=href;});",
        "});",
        "const headings=sidebar.querySelectorAll('[data-testid=\"stSidebarNav\"] h2,[data-testid=\"stSidebarNav\"] h3,[data-testid=\"stSidebarNav\"] h4');",
        "headings.forEach(heading=>{",
        "const label=(heading.textContent||'').trim();",
        "const item=SECTION_HOMES.find(x=>x.label===label);",
        "if(!item||heading.dataset.sectionHomeBound==='1')return;",
        "heading.dataset.sectionHomeBound='1';",
        "heading.setAttribute('role','link');",
        "heading.setAttribute('tabindex','0');",
        "const go=()=>{window.location.assign(homeHrefs[item.key]||('/'+item.key));};",
        "heading.addEventListener('click',go);",
        "heading.addEventListener('keydown',event=>{",
        "if(event.key==='Enter'||event.key===' '){event.preventDefault();go();}",
        "});",
        "});",
        "}",
        "const root=document.querySelector('#root')||document.body;",
        "const obs=new MutationObserver(()=>bindSectionHomes());",
        "obs.observe(root,{childList:true,subtree:true});",
        "bindSectionHomes();",
        "setTimeout(bindSectionHomes,100);",
        "setTimeout(bindSectionHomes,500);",
        "setTimeout(bindSectionHomes,1500);",
        "})();",
        "</script>",
    ]

    st.markdown("\n".join(css_lines + js_lines), unsafe_allow_html=True)


navigation_sections = {}
for section in PAGE_SECTIONS:
    pages = [_page_from_spec(spec) for spec in section.pages]
    navigation_sections[section.title] = [page for page in pages if page]

_sidebar_home_behavior()
_show_preflight_warnings()

pg = st.navigation(navigation_sections, expanded=False)
pg.run()
