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

st.set_page_config(page_title="出貨課", page_icon="🚚", layout="wide")
inject_logistics_theme()

ITEMS = (
    HomeNavItem(
        "🚚",
        "撥貨差異",
        "比對撥貨來源與查詢資料，整理差異與儲位資訊。",
        "pages/6_撥貨差異.py",
    ),
    HomeNavItem(
        "📦",
        "採品門市差異量",
        "彙整採品與門市差異量，支援出貨異常檢核。",
        "pages/23_採品門市差異量.py",
    ),
    HomeNavItem(
        "🏭",
        "出貨作業線產能",
        "分析每日出貨作業線產能與人員效率。",
        "pages/24_出貨作業線產能.py",
    ),
    HomeNavItem(
        "⏱️",
        "各時段作業效率",
        "依時段、線別與區域檢視 PCS、PASS/FAIL 與效率。",
        "pages/29_各時段作業效率.py",
    ),
    HomeNavItem(
        "🧾",
        "客訂差異",
        "比對客訂差異、庫存與儲位，產出可追蹤明細。",
        "pages/30_客訂差異.py",
    ),
)


def main():
    route_home_nav([item.page_path for item in ITEMS])

    set_page("出貨課", icon="🚚", subtitle="出貨差異、產能與效率分析入口。")

    card_open("出貨課功能")
    render_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
