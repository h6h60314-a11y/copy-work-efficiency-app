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

# ✅ 出貨課：先只放「出貨課首頁」（其餘模組從首頁進入）
out_home_page = st.Page("pages/7_出貨課首頁.py", title="出貨課首頁", icon="📦")

# ✅ 進貨課：先只放「進貨課首頁」（其餘模組從首頁進入）
in_home_page = st.Page("pages/8_進貨課首頁.py", title="進貨課首頁", icon="🚚")

# =========================
# Navigation（左側欄只保留課別入口）
# =========================
pg = st.navigation(
    {
        "": [home_page],
        "📦 出貨課": [out_home_page],
        "🚚 進貨課": [in_home_page],
    },
    expanded=False,
)

pg.run()
