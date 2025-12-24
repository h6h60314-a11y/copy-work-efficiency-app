# pages/7_出貨課首頁.py
import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 出貨課", page_icon="📦", layout="wide")
inject_logistics_theme()

set_page("出貨課", icon="📦", subtitle="Outbound｜出貨相關模組入口")

card_open("📦 出貨課模組")
st.markdown("請選擇下列模組：")

col1, col2 = st.columns(2)
with col1:
    if st.button("📦 撥貨差異", use_container_width=True):
        st.switch_page("pages/1_撥貨差異.py")

# 你之後要加出貨課其他項目，就照這個格式往下加
# with col2:
#     if st.button("📤 出貨作業效能", use_container_width=True):
#         st.switch_page("pages/XX_出貨作業效能.py")

card_close()
