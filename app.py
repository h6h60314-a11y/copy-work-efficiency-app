import streamlit as st

# =========================================
# App Config
# =========================================
st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",  # 依你的專案調整路徑
    layout="wide",
)

# =========================================
# Sidebar CSS（✅ 首頁最大字、✅ 進貨課次大字 + 🚚、✅ 不受 Streamlit DOM 變動影響）
# =========================================
st.markdown(
    """
<style>
/* ===== Sidebar 基本 ===== */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* ===== 全部選單：預設字級 ===== */
section[data-testid="stSidebar"] nav a *,
section[data-testid="stSidebar"] nav button *{
  font-size: 15px !important;
  font-weight: 650 !important;
  line-height: 1.25 !important;
  text-decoration: none !important;
}

/* ✅ 首頁：Sidebar Nav 裡「第一個可點項目」→ 最大字
   Streamlit 不同版本可能用 a / button / li 結構，所以多組 selector 疊加命中 */
div[data-testid="stSidebarNav"] li:first-child a *,
div[data-testid="stSidebarNav"] li:first-child button *,
div[data-testid="stSidebarNav"] a:first-of-type *,
div[data-testid="stSidebarNav"] button:first-of-type *{
  font-size: 26px !important;
  font-weight: 900 !important;
}

/* ✅ 群組標題（進貨課）：不是可點連結的那一行 → 次大字 */
div[data-testid="stSidebarNav"] span:not(a span):not(button span),
div[data-testid="stSidebarNav"] p:not(a p):not(button p),
div[data-testid="stSidebarNav"] div:not(a div):not(button div){
  font-size: 20px !important;
  font-weight: 850 !important;
  display: flex;
  align-items: center;
  letter-spacing: 0.5px;
}

/* ✅ 群組標題前加 🚚（只作用在群組標題，不影響子頁項目） */
div[data-testid="stSidebarNav"] span:not(a span):not(button span)::before,
div[data-testid="stSidebarNav"] p:not(a p):not(button p)::before,
div[data-testid="stSidebarNav"] div:not(a div):not(button div)::before{
  content: "🚚 ";
  font-size: 22px;
  margin-right: 4px;
}

/* 保險：不要讓子頁 a/button 的文字被 ::before 汙染 */
div[data-testid="stSidebarNav"] a *::before,
div[data-testid="stSidebarNav"] button *::before{
  content: "" !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================
# Pages（依你目前的檔名）
# =========================================
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# =========================================
# Navigation
# - ""：只放首頁 → 不顯示群組標題 → 不會有下拉
# - 進貨課：預設收合 expanded=False（不點不展開）
# =========================================
pg = st.navigation(
    {
        "": [home_page],
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,
)

pg.run()
