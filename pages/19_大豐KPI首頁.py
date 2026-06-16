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

st.set_page_config(page_title="大豐 KPI", page_icon="📈", layout="wide")
inject_logistics_theme()

ITEMS = (
    HomeNavItem(
        "✅",
        "進貨課 - 驗收量體",
        "統計 QC 驗收量體與進貨驗收作業指標。",
        "pages/20_進貨課 - 驗收量體.py",
    ),
    HomeNavItem(
        "🚚",
        "進貨課 - 上架量體",
        "彙整上架量體、儲位與進貨作業資料。",
        "pages/21_進貨課 - 上架量體.py",
    ),
    HomeNavItem(
        "📊",
        "儲位使用率",
        "分析儲位容量、使用量與不同儲區使用率。",
        "pages/4_儲位使用率.py",
    ),
    HomeNavItem(
        "📌",
        "進貨課 - 總揀筆數",
        "統計總揀筆數與進貨課作業量體。",
        "pages/22_進貨課 - 總揀筆數.py",
    ),
    HomeNavItem(
        "📋",
        "每日庫存應作量",
        "計算每日庫存應作量與未完成量體。",
        "pages/28_每日庫存應作量.py",
    ),
    HomeNavItem(
        "⏱️",
        "整體作業工時",
        "整理整體作業工時與人力投入資料。",
        "pages/25_整體作業工時.py",
    ),
    HomeNavItem(
        "📦",
        "整體作業量體",
        "彙整整體作業量體、出貨與進貨關鍵指標。",
        "pages/26_整體作業量體.py",
    ),
)


def main():
    route_home_nav([item.page_path for item in ITEMS])

    set_page("大豐 KPI", icon="📈", subtitle="大豐 KPI 量體、工時與儲位分析入口。")

    card_open("大豐 KPI 功能")
    render_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
