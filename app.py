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
# Sidebar CSS（依你截圖 DOM：首頁=nav 第一個 a）
# =========================================
st.markdown(
    """
<style>
/* Sidebar padding */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* 所有選單：預設字級 */
section[data-testid="stSidebar"] nav a span{
  font-size: 15px !important;
  font-weight: 650 !important;
  text-decoration: none !important;
}

/* ✅ 首頁：Sidebar 導覽第一個項目 → 最大字 */
section[data-testid="stSidebar"] nav a:first-of-type span{
  font-size: 26px !important;
  font-weight: 900 !important;
}

/* ✅ 群組標題「進貨課」：不是 link 的那一行 → 次大字 */
section[data-testid="stSidebarNav"] span:not(a span){
  font-size: 20px !important;
  font-weight: 850 !important;
  display: flex;
  align-items: center;
  letter-spacing: 0.5px;
}

/* ✅ 群組標題前加 🚚（只加在群組標題，不影響子項） */
section[data-testid="stSidebarNav"] span:not(a span)::before{
  content: "🚚 ";
  font-size: 22px;
  margin-right: 4px;
}

/* 保險：不要讓 a/span 被 ::before 汙染 */
section[data-testid="stSidebar"] nav a span::before{
  content: "" !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================
# Pages（依你目前檔名）
# =========================================
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page(
    "pages/5_揀貨差異代庫存.py",
    title="揀貨差異代庫存",
    icon="🔎",
)

# =========================================
# Navigation
# - ""：只放首頁 → 不顯示群組標題 → 不會下拉
# - 進貨課：預設收合 expanded=False
# =========================================
pg = st.navigation(
    {
        "": [home_page],
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,
)

pg.run()
