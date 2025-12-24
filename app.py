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

/* ===== ✅ 首頁最大：修重疊（flex + 增高 + icon不縮） ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a{
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  padding-top: 12px !important;
  padding-bottom: 12px !important;
  min-height: 52px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.25 !important;
  white-space: nowrap !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a svg{
  width: 24px !important;
  height: 24px !important;
  flex: 0 0 auto !important;
  transform: translateY(1px);
}

/* ===== ✅ 群組標題次大：鎖「有子選單的父節點」(進貨課) =====
   li:has(ul) 代表這個 li 底下還有一個 ul（子選單）
   我們只放大「ul 以外」的那一段（也就是群組標題那行），子項不受影響
*/
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul){
  margin-top: 6px !important;
}

/* 群組標題那一行（ul 以外的區塊）放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul) *{
  font-size: 22px !important;
  font-weight: 900 !important;
  line-height: 1.2 !important;
}

/* 群組標題那一行留白 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul){
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* 群組標題 icon/caret 同步放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul) svg{
  width: 20px !important;
  height: 20px !important;
  transform: translateY(1px);
}

/* ✅ 子選單（ul 內）強制回到子項大小，避免被群組標題放大吃到 */
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
