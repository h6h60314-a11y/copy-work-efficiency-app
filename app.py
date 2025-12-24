# app.py
import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",
    layout="wide",
)

st.markdown(
    r"""
<style>
/* Sidebar base */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* ===== 子項：所有頁面連結（固定正常大小） ===== */
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

/* ===== ✅ 首頁最大：強制靠左排列（解決「文字置中導致距離很大」） ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a{
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;  /* ✅ 靠左 */
  gap: 6px !important;                    /* ✅ icon-文字距離 */
  padding: 10px 12px !important;          /* ✅ 左右內距 */
  min-height: 48px !important;
}

/* 把首頁內部所有「可能在撐寬/置中」的容器重置掉 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a > *{
  flex: 0 0 auto !important;
  margin-left: 0 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  text-align: left !important;
}

/* 清掉 p/span 預設 margin，避免擠壓 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a p,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a span{
  margin: 0 !important;
  padding: 0 !important;
}

/* 首頁文字放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.15 !important;
  white-space: nowrap !important;
}

/* 首頁 icon：支援 svg / emoji(span) */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a svg{
  width: 20px !important;
  height: 20px !important;
  flex: 0 0 auto !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a span{
  font-size: 20px !important;
  line-height: 1 !important;
}

/* ===== ✅ 群組標題次大：任何「li 底下有 ul」的父節點 ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul){
  margin-top: 6px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul) *{
  font-size: 22px !important;
  font-weight: 900 !important;
  line-height: 1.2 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul){
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* 子選單（ul 內）回到正常大小 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) ul a *{
  font-size: 16px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# Pages
# =========================
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

# 出貨課
out_home_page = st.Page("pages/7_出貨課首頁.py", title="出貨課首頁", icon="📦")
transfer_diff_page = st.Page("pages/1_撥貨差異.py", title="撥貨差異", icon="📦")

# 進貨課
in_home_page = st.Page("pages/8_進貨課首頁.py", title="進貨課首頁", icon="🚚")
qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# =========================
# Navigation（左側：課別 + 項目都顯示）
# =========================
pg = st.navigation(
    {
        "": [home_page],
        "📦 出貨課": [out_home_page, transfer_diff_page],
        "🚚 進貨課": [in_home_page, qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,
)

pg.run()
