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

st.set_page_config(page_title="大豐物流作業平台", page_icon="🏠", layout="wide")
inject_logistics_theme()

ITEMS = (
    HomeNavItem(
        "🧭",
        "企劃課",
        "拉單明細整理與作業資料前置處理。",
        "pages/31_企劃課首頁.py",
    ),
    HomeNavItem(
        "🚚",
        "出貨課",
        "撥貨差異、出貨產能、各時段效率與客訂差異分析。",
        "pages/7_出貨課首頁.py",
    ),
    HomeNavItem(
        "📥",
        "進貨課",
        "驗收、上架、總揀、少揀與 QC 未上架比對。",
        "pages/8_進貨課首頁.py",
    ),
    HomeNavItem(
        "📊",
        "大樹 KPI",
        "大樹相關進出貨量體、庫存、門市到貨與儲區使用率。",
        "pages/9_大樹KPI首頁.py",
    ),
    HomeNavItem(
        "📈",
        "大豐 KPI",
        "大豐整體作業量體、工時、庫存應作量與進貨課量體。",
        "pages/19_大豐KPI首頁.py",
    ),
)


def main():
    route_home_nav([item.page_path for item in ITEMS])

    set_page(
        "大豐物流作業平台",
        icon="🏠",
        subtitle="整合作業效率、KPI、差異分析與工時計算。",
    )

    card_open("作業入口")
    render_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
