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
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# ===== Navigation =====
# 目標：
# 1) 首頁只顯示一個，不要「首頁」群組的下拉
# 2) 進貨課預設收合，不點就不顯示子項目
pg = st.navigation(
    [
        home_page,  # ✅ 直接放在最外層 → Sidebar 只會有一個「首頁」
        {
            "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
            "collapsed": True,  # ✅ 預設收合 → 不點不會展開子項
        },
    ]
)

pg.run()
