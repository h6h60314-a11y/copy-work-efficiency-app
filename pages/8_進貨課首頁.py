# pages/8_進貨課首頁.py
import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 進貨課", page_icon="🚚", layout="wide")
inject_logistics_theme()

set_page("進貨課", icon="🚚", subtitle="Inbound｜進貨相關模組入口")

card_open("🚚 進貨課模組")
st.markdown("請選擇下列模組：")

col1, col2 = st.columns(2)

with col1:
    if st.button("✅ 驗收作業效能", use_container_width=True):
        st.switch_page("pages/1_驗收作業效能.py")
    if st.button("🎯 總揀作業效能", use_container_width=True):
        st.switch_page("pages/3_總揀作業效能.py")
    if st.button("🔎 揀貨差異代庫存", use_container_width=True):
        st.switch_page("pages/5_揀貨差異代庫存.py")

with col2:
    if st.button("📦 上架作業效能", use_container_width=True):
        st.switch_page("pages/2_上架作業效能.py")
    if st.button("🧊 儲位使用率", use_container_width=True):
        st.switch_page("pages/4_儲位使用率.py")

card_close()
