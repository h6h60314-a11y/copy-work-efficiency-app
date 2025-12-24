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

/* ===== ✅ 首頁最大：不重疊 + 距離更緊 ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a{
  display: grid !important;
  grid-template-columns: 22px 1fr !important; /* ✅ icon 欄位縮小 */
  align-items: center !important;
  column-gap: 6px !important;               /* ✅ 間距縮小 */
  padding-top: 10px !important;
  padding-bottom: 10px !important;
  min-height: 48px !important;              /* ✅ 高度縮小 */
}

/* 清掉 p/span margin，避免字體放大又擠壓 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a p,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a span{
  margin: 0 !important;
  padding: 0 !important;
}

/* 首頁文字放大（可微調：28~30 你覺得太大再降） */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.15 !important;
  white-space: nowrap !important;
}

/* icon：支援 svg/emoji，置中並縮一點 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a svg,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a span{
  justify-self: center !important;
  align-self: center !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a svg{
  width: 20px !important;
  height: 20px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a span{
  font-size: 20px !important;   /* emoji icon */
  line-height: 1 !important;
}

/* ===== ✅ 群組標題次大：進貨課 ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul){
  margin-top: 10px !important;
}

/* 群組標題那一行（ul 以外的區塊）放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul) *{
  font-size: 22px !important;
  font-weight: 900 !important;
  line-height: 1.2 !important;
}

/* 群組標題留白 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul){
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* 子選單（ul 內）強制回子項大小 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) ul a *{
  font-size: 16px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
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

