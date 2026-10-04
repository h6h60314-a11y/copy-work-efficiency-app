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


st.set_page_config(page_title="Handover", page_icon="⏱️", layout="wide")
inject_logistics_theme()


ITEMS = (
    HomeNavItem(
        "📦",
        "揀貨作業",
        "整合揀貨成箱、訂單 Line、零散 PCS 與零散總揀，四套邏輯獨立計算。",
        "pages/35_Handover_揀貨作業.py",
    ),
)


def main():
    route_home_nav([item.page_path for item in ITEMS])

    set_page(
        "Handover",
        icon="⏱️",
        subtitle="Handover 作業量、完成狀態與稼動指標分析入口。",
    )

    card_open("Handover功能")
    render_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
