import streamlit as st
from common_ui import inject_logistics_theme

st.set_page_config(
    page_title="倉儲營運效能平台",
    page_icon="🏭",
    layout="wide",
)

inject_logistics_theme()

def main():
    st.markdown("## 🏭 倉儲營運效能平台")
    st.caption("第三方物流｜作業KPI｜稽核留存｜管理復盤")

    st.markdown("### 功能導覽")
    st.markdown(
        """
- ✅ **驗收作業效能（KPI）**：驗收人員效率、達標率、AM/PM 班別切分、排除區間
- 📦 **上架產能分析（Putaway KPI）**：上架產能、人時效率、班別/區塊規則
- 📊 **營運稽核與復盤中心**：歷次執行留存、趨勢圖、下載當次報表
        """
    )

    st.info("請從左側選單切換模組。若主管要回溯檢討，請直接進入「營運稽核與復盤中心」。")

if __name__ == "__main__":
    main()
