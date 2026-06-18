from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import streamlit as st

from nav_config import APP_ICON, APP_TITLE, PAGE_SECTIONS, PageSpec
from sidebar_ui import render_sidebar


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


pg = st.navigation(all_pages(), position="hidden")
render_sidebar(PAGE_SECTIONS)
pg.run()
