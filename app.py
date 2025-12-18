import streamlit as st

# ===== 頁面基本設定（影響左側選單名稱）=====
st.set_page_config(
    page_title="工作效率平台",
    page_icon="🏭",
    layout="wide"
)

# ===== 首頁標題 =====
st.title("🏭 工作效率平台")

st.markdown(
    """
### 左側選單可切換不同項目（主管快速看版）

- ✅ **驗收達標效率**  
  （含空窗 / AM-PM / 排除區間）

- 📦 **總上組上架產能**  
  （含空窗 / AM-PM / 報表區塊 / 休息規則）

---

**操作流程：**  
📤 上傳檔案 → ⚙️ 設定參數（如需） → 🚀 開始計算 → ⬇️ 下載 Excel
"""
)

st.info("請由左側選單選擇要查看的功能項目。")
