import streamlit as st

from common_ui import (
    HomeNavItem,
    card_close,
    card_open,
    inject_logistics_theme,
    render_home_nav,
    route_home_nav,
    set_page,
)


st.set_page_config(page_title="報工稼動", page_icon="⏱️", layout="wide")
inject_logistics_theme()


ITEMS = (
    HomeNavItem(
        "📦",
        "揀貨成箱",
        "彙整揀貨成箱 Line、完成狀態與應作業／實際作業 PCS。",
        "pages/35_報工稼動 | 揀貨成箱.py",
    ),
    HomeNavItem(
        "🎯",
        "零散總揀",
        "彙整零散總揀應作業 Line、實際完成 Line 與完成率。",
        "pages/37_報工稼動 | 零散總揀.py",
    ),
)


def main():
    route_home_nav([item.page_path for item in ITEMS])

    set_page(
        "報工稼動",
        icon="⏱️",
        subtitle="報工作業量、完成狀態與稼動指標分析入口。",
    )

    card_open("報工稼動功能")
    render_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
