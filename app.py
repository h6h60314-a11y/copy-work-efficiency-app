import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",
    layout="wide",
)

# ===== Pages =====
home_page = st.Page(
    "pages/0_首頁.py",
    title="首頁",
    icon="🏠",
    default=True,
)

qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page(
    "pages/5_揀貨差異代庫存.py",
    title="揀貨差異代庫存",
    icon="🔎",
)

# ✅ 重要：
# 1) 首頁放到「空白群組」 -> Sidebar 只顯示一個「首頁」，不會出現下拉群組
# 2) expanded=False -> 群組預設收合 -> 進貨課不點就不展開
pg = st.navigation(
    {
        "": [home_page],  # ✅ 不顯示群組標題，只剩一個首頁項目
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,  # ✅ 預設全部群組收合（進貨課會收合）
)

pg.run()
