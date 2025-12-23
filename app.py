import streamlit as st


# =========================================
# App Config
# =========================================
st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",
    layout="wide",
)


# =========================================
# Navigation (Sidebar Groups)
#   - 「作業模組」→「進貨課」
#   - 避免 recursion：不要把 app.py 當作 Page 跑
# =========================================
home_page = st.Page(
    "pages/0_首頁.py",
    title="首頁",
    icon="🏠",
    default=True,
)

qc_page = st.Page(
    "pages/1_驗收作業效能.py",
    title="驗收作業效能",
    icon="✅",
)

putaway_page = st.Page(
    "pages/2_上架作業效能.py",
    title="上架作業效能",
    icon="📦",
)

pick_page = st.Page(
    "pages/3_總揀作業效能.py",
    title="總揀作業效能",
    icon="🎯",
)

slot_page = st.Page(
    "pages/4_儲位使用率.py",
    title="儲位使用率",
    icon="🧊",
)

diff_page = st.Page(
    "pages/5_揀貨差異代庫存.py",
    title="揀貨差異代庫存",
    icon="🔎",
)

pg = st.navigation(
    {
        "首頁": [home_page],
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],  # ✅ 改名在這行
    }
)

pg.run()

