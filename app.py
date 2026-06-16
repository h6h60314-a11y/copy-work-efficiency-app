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


pg = st.navigation(_navigation_pages(), expanded=False)
_show_preflight_warnings()
pg.run()
