# pages/31_企劃課首頁.py
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="企劃課", page_icon="🧩", layout="wide")
inject_logistics_theme()


def _item(icon: str, title: str, page_path: str, desc: str):
    cols = st.columns([0.02, 0.98])

    with cols[0]:
        st.markdown("•")

    with cols[1]:
        st.page_link(
            page_path,
            label=f"{icon}  {title}",
        )
        st.markdown(f"　　{desc}")


def main():
    set_page("企劃課", icon="🧩", subtitle="Planning｜企劃分析與行政作業入口")

    card_open("🧩 企劃課模組")

    _item(
        "📄",
        "拉單明細",
        "pages/32_拉單明細.py",
        "多檔拉單明細合併整理，保留指定欄位並產出單一 Excel 檔",
    )

    _item(
        "📊",
        "倉儲使用率分析",
        "pages/倉儲使用率分析.py",
        "依儲位類型、使用狀態與容量資料，分析倉儲使用率與空位狀況",
    )

    _item(
        "📋",
        "行政 KPI 量化",
        "pages/行政KPI量化.py",
        "彙整行政任務、回覆時效、作業完成率與扣分紀錄",
    )

    _item(
        "📦",
        "盤點差異分析",
        "pages/盤點差異分析.py",
        "整理盤點差異、商品異常、效期與庫存比對結果",
    )

    _item(
        "🧾",
        "會議紀錄整理",
        "pages/會議紀錄整理.py",
        "整理會議內容、待辦事項、責任歸屬與追蹤進度",
    )

    _item(
        "⚙️",
        "自動化工具",
        "pages/自動化工具.py",
        "放置企劃課常用批次處理、Excel 轉換與報表產出工具",
    )

    card_close()


if __name__ == "__main__":
    main()
