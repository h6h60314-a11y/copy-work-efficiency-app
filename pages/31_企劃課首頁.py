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
        "📄",
        "拉單明細",
        "pages/32_拉單明細.py",
        "多檔拉單明細合併整理，保留指定欄位並產出單一 Excel 檔",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    card_close()


if __name__ == "__main__":
    main()
