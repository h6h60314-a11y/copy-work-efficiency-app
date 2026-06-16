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

st.set_page_config(page_title="大樹 KPI", page_icon="📊", layout="wide")
inject_logistics_theme()

ITEMS = (
    HomeNavItem(
        "📥",
        "進貨驗收量",
        "統計進貨驗收量與相關量體指標。",
        "pages/10_進貨驗收量.py",
    ),
    HomeNavItem(
        "🚚",
        "庫存訂單應出量分析",
        "分析庫存訂單應出量、箱數與品項彙總。",
        "pages/11_庫存訂單應出量分析.py",
    ),
    HomeNavItem(
        "🧾",
        "越庫訂單分析",
        "整理越庫訂單資料，檢視不同狀態與作業量。",
        "pages/12_越庫訂單分析.py",
    ),
    HomeNavItem(
        "✅",
        "庫存訂單實出量分析",
        "分析庫存訂單實出量、出貨件數與差異。",
        "pages/13_庫存訂單實出量分析.py",
    ),
    HomeNavItem(
        "🚚",
        "每日上架分析",
        "彙整每日上架量體與儲位相關資訊。",
        "pages/14_每日上架分析.py",
    ),
    HomeNavItem(
        "📌",
        "庫存盤點正確率",
        "計算盤點正確率與異常項目。",
        "pages/15_庫存盤點正確率.py",
    ),
    HomeNavItem(
        "⚠️",
        "門市到貨異常率",
        "分析門市到貨異常數、異常率與明細。",
        "pages/16_門市到貨異常率.py",
    ),
    HomeNavItem(
        "⏱️",
        "每日出勤工時分析",
        "整理每日出勤與工時計算資料。",
        "pages/17_每日出勤工時分析.py",
    ),
    HomeNavItem(
        "📊",
        "各類儲區使用率",
        "計算各類儲區容量、使用量與使用率。",
        "pages/18_各類儲區使用率.py",
    ),
)


def main():
    route_home_nav([item.page_path for item in ITEMS])

    set_page("大樹 KPI", icon="📊", subtitle="大樹 KPI 量體、庫存與異常分析入口。")

    card_open("大樹 KPI 功能")
    render_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
