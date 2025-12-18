import streamlit as st
from common_ui import inject_purple_theme, set_page

st.set_page_config(
    page_title="工作效率平台",
    page_icon="🏭",
    layout="wide",
)

inject_purple_theme()

def main():
    set_page("工作效率平台", icon="🏭")
    st.markdown("### 入口首頁")
    st.write("請從左側選單切換功能：")
    st.write("- ✅ 驗收達標效率")
    st.write("- 📦 總上組上架產能")
    st.write("- 📊 總檢討中心")

if __name__ == "__main__":
    main()
