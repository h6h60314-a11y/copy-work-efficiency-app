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


st.set_page_config(page_title="企劃課", page_icon="🧭", layout="wide")
inject_logistics_theme()


ITEMS = (
    HomeNavItem(
        "📋",
        "拉單明細",
        "整理拉單明細欄位與格式，產出可接續作業的 Excel 檔。",
        "pages/32_拉單明細.py",
    ),
    HomeNavItem(
        "📦",
        "月出貨量與產力",
        "上傳商品主檔與月出貨資料，自動完成出貨量計算、SKU 比對及彙總。",
        "pages/34_月出貨量與產力.py",
    ),
)


def main():
    route_home_nav([item.page_path for item in ITEMS])

    set_page("企劃課", icon="🧭", subtitle="企劃資料整理與作業前置入口。")

    card_open("企劃課功能")
    render_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
