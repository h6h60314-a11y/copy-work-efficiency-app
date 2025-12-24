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

/* ===== 子項：所有連結（基準） ===== */
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

/* ===== ✅ 群組標題：🚚 進貨課（次大）=====
   你的版本「群組標題」看起來是第一層 ul 裡的 li > div 那行 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li > div *{
  font-size: 22px !important;
  font-weight: 900 !important;
  line-height: 1.2 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li > div{
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* ===== ✅ 首頁（字最大）— 重點：用 flex + 增高 + icon 不縮，避免重疊 ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a{
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  padding-top: 12px !important;
  padding-bottom: 12px !important;
  min-height: 52px !important;   /* ✅ 增高：避免大字擠壓 */
}

/* 首頁文字放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.25 !important; /* ✅ 拉開行高：避免上下壓到 */
  white-space: nowrap !important; /* ✅ 單行顯示，避免換行造成擠壓 */
}

/* 首頁 icon 放大且不縮 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a svg{
  width: 24px !important;
  height: 24px !important;
  flex: 0 0 auto !important;    /* ✅ icon 不縮 */
  transform: translateY(1px);
}
</style>
""",
    unsafe_allow_html=True,
)

# Pages
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
