# pages/31_企劃課首頁.py
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="企劃課", page_icon="🧩", layout="wide")
inject_logistics_theme()


def _css():
    st.markdown(
        """
<style>
.planning-list {
    margin-top: 8px;
}

.planning-item {
    padding: 10px 4px 12px 4px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.22);
}

.planning-desc {
    margin-top: -4px;
    margin-left: 34px;
    color: rgba(15, 23, 42, 0.68);
    font-size: 14px;
    font-weight: 650;
    line-height: 1.55;
}

div[data-testid="stPageLink"] {
    margin: 0 !important;
}

div[data-testid="stPageLink"] a {
    font-weight: 900 !important;
    font-size: 16px !important;
    color: rgba(15, 23, 42, 0.94) !important;
    text-decoration: none !important;
}

div[data-testid="stPageLink"] a:hover {
    opacity: 0.86;
    text-decoration: none !important;
}

div[data-testid="stMarkdown"] {
    margin-bottom: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _nav_item(icon: str, title: str, page_path: str, desc: str):
    st.markdown('<div class="planning-item">', unsafe_allow_html=True)

    st.page_link(
        page_path,
        label=title,
        icon=icon,
    )

    st.markdown(
        f'<div class="planning-desc">{desc}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


def main():
    set_page("企劃課", icon="🧩", subtitle="Planning｜企劃分析與行政作業入口")

    card_open("🧩 企劃課模組")
    _css()

    st.markdown('<div class="planning-list">', unsafe_allow_html=True)

    _nav_item(
        "📊",
        "倉儲使用率分析",
        "pages/倉儲使用率分析.py",
        "依儲位類型、使用狀態與容量資料，分析倉儲使用率與空位狀況",
    )

    _nav_item(
        "📋",
        "行政 KPI 量化",
        "pages/行政KPI量化.py",
        "彙整行政任務、回覆時效、作業完成率與扣分紀錄",
    )

    _nav_item(
        "📦",
        "盤點差異分析",
        "pages/盤點差異分析.py",
        "整理盤點差異、商品異常、效期與庫存比對結果",
    )

    _nav_item(
        "🧾",
        "會議紀錄整理",
        "pages/會議紀錄整理.py",
        "整理會議內容、待辦事項、責任歸屬與追蹤進度",
    )

    _nav_item(
        "⚙️",
        "自動化工具",
        "pages/自動化工具.py",
        "放置企劃課常用批次處理、Excel 轉換與報表產出工具",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    card_close()


if __name__ == "__main__":
    main()
