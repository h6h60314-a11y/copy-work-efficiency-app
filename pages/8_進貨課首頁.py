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

st.set_page_config(page_title="進貨課", page_icon="📥", layout="wide")
inject_logistics_theme()

ITEMS = (
    HomeNavItem(
        "✅",
        "驗收作業效能",
        "計算驗收作業效率、AM/PM 分析與排除時段後的 KPI。",
        "pages/1_驗收作業效能.py",
    ),
    HomeNavItem(
        "🚚",
        "上架作業效能",
        "分析上架作業產能、人員效率與匯出檢核報表。",
        "pages/2_上架作業效能.py",
    ),
    HomeNavItem(
        "📌",
        "總揀作業效能",
        "彙整總揀作業時段、件數與人員效率。",
        "pages/3_總揀作業效能.py",
    ),
    HomeNavItem(
        "📦",
        "揀貨差異代庫存",
        "處理少揀差異、儲位對應與代庫存明細。",
        "pages/5_揀貨差異代庫存.py",
    ),
    HomeNavItem(
        "🧾",
        "QC 未上架比對",
        "比對 QC 與未上架資料，整理待追蹤作業差異。",
        "pages/27_QC未上架比對.py",
    ),
)


def main():
    route_home_nav([item.page_path for item in ITEMS])

    set_page("進貨課", icon="📥", subtitle="進貨作業效率、差異與 QC 比對入口。")

    card_open("進貨課功能")
    render_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
