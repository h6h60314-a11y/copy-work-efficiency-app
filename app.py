import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="進貨課效能平台",
    page_icon="🏭",
    layout="wide",
)

inject_logistics_theme()

def main():
    set_page("進貨課效能平台", icon="🏭")
    st.caption("作業KPI｜AM/PM ")

    card_open("📌 模組導覽")
    st.markdown(
        """
- ✅ **驗收作業效能（KPI）**：人時效率、達標率、AM/PM 班別切分、排除非作業區間
- 📦 **上架產能分析（Putaway KPI）**：上架產能、人時效率、區塊/報表規則、班別切分
        """
    card_close()

if __name__ == "__main__":
    main()

