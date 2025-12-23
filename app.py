import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="進貨課效能平台",
    page_icon="🏭",
    layout="wide",
)

inject_logistics_theme()


def main():
    set_page("進貨課效能平台", icon="🏭", subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間")

    card_open("📌 模組導覽")
    st.markdown(
        """
- ✅ **驗收作業效能（KPI）**：人時效率、達標率、班別（AM/PM）切分、支援/離站等非作業區間排除  
- 📦 **上架產能分析（Putaway KPI）**：上架產能、人時效率、班別（AM/PM）切分、報表匯出  
- 🎯 **總揀達標**：分上午/下午達標、低空/高空門檻、排除非作業區間、匯出報表  
- 🧊 **儲位使用率**：依區(溫層)分類統計、使用率>門檻紅色提示、分類可調整、報表匯出  
        """
    )
    card_close()

    st.divider()
    st.caption("提示：左側選單可切換各模組頁面；各頁面的「計算條件設定」只影響本次分析結果。")


if __name__ == "__main__":
    main()
