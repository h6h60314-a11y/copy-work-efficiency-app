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


    card_close()


if __name__ == "__main__":
    main()
