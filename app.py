import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",
    layout="wide",
)

# =========================
# Sidebar CSS（不靠 :has、不靠 aria-expanded）
# 目標：
# - 首頁最大
# - 群組標題（🚚 進貨課）次大
# - 子項維持正常
# =========================
st.markdown(
    r"""
<style>
/* Sidebar base */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* ===== 子項：所有連結（驗收/上架/總揀/儲位/揀貨差異...） ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a{
  text-decoration: none !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a *{
  font-size: 16px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li a{
  padding-top: 8px !important;
  padding-bottom: 8px !important;
}

/* ===== ✅ 群組標題：第一層清單裡「li 的 direct child 是 div」那一行 =====
   在你的畫面中「進貨課」不像連結（不是 a），而是 div 容器的一列，所以用這個抓最穩 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li > div *{
  font-size: 22px !important;
  font-weight: 900 !important;
  line-height: 1.2 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li > div{
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* ===== ✅ 首頁最大：優先用 href 命中；若 href 結構不同，fallback 用第一個 li 的 a ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="pages/0_首頁.py"] *,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="0_%E9%A6%96%E9%A0%81"] *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.12 !important;
}

/* fallback：如果 href 抓不到，就把第一個 li 的 a 當成首頁放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.12 !important;
}

/* 首頁 icon 放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a svg{
  width: 24px !important;
  height: 24px !important;
  transform: translateY(2px);
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# Pages
# =========================
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

pg = st.navigation(
    {
        "": [home_page],
        "🚚 進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,
)

pg.run()
