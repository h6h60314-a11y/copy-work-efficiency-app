import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",
    layout="wide",
)

st.markdown(
    r"""
<style>
/* ========== Sidebar base ========== */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* 子項（一般頁面連結）基準字體 */
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

/* ========== ✅ 群組標題（🚚 進貨課）= 有子選單的那一列：li 裡面會包含 ul ========== */
/* 命中群組標題文字（只影響群組那一行，不影響子項） */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(ul) > div:first-child *{
  font-size: 22px !important;
  font-weight: 900 !important;
  line-height: 1.2 !important;
}

/* 群組標題那一列增加留白 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(ul) > div:first-child{
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* 群組標題的 icon/caret 也放大（避免看起來還是很小） */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:has(ul) > div:first-child svg{
  width: 20px !important;
  height: 20px !important;
  transform: translateY(2px);
}

/* ========== ✅ 首頁（字最大）：仍用 href 精準鎖 0_首頁 ========== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="pages/0_首頁.py"] *,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="0_%E9%A6%96%E9%A0%81"] *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.12 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="pages/0_首頁.py"] svg,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="0_%E9%A6%96%E9%A0%81"] svg{
  width: 24px !important;
  height: 24px !important;
  transform: translateY(2px);
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="pages/0_首頁.py"],
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="0_%E9%A6%96%E9%A0%81"]{
  padding-top: 12px !important;
  padding-bottom: 12px !important;
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
