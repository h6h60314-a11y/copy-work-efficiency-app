import streamlit as st

st.set_page_config(page_title="工作效率平台", layout="wide")
st.title("🏭 工作效率平台")

st.markdown("""
左側選單可切換不同項目（主管快速看版）：

- ✅ **驗收達標效率**（含空窗 / AM-PM / 排除區間）
- 📦 **總上組上架產能**（含空窗 / AM-PM / 報表_區塊 / 休息規則）

> 操作：上傳檔案 → 設定參數（如需）→ 開始計算 → 下載 Excel
""")
