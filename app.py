import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",  # 依你的專案路徑調整
    layout="wide",
)

# =========================
# Sidebar CSS（修正版：不亂加圖示）
# =========================
st.markdown(
    """
<style>
/* Sidebar padding */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* 先把 sidebar 裡所有文字統一回正常狀態（避免被其他 CSS 汙染） */
section[data-testid="stSidebar"] nav a,
section[data-testid="stSidebar"] nav button{
  text-decoration: none !important;
}
section[data-testid="stSidebar"] nav a *,
section[data-testid="stSidebar"] nav button *{
  font-size: 15px !important;
  font-weight: 650 !important;
  line-height: 1.25 !important;
}

/* ✅ 首頁：sidebar 導覽第一個可點項目 → 最大字 */
div[data-testid="stSidebarNav"] li:first-child a *,
div[data-testid="stSidebarNav"] li:first-child button *{
  font-size: 26px !important;
  font-weight: 900 !important;
}

/* ✅ 進貨課：只鎖「群組標題」本身（Streamlit 會用 header/div 包一層）
   這裡不使用 ::before 掃全局，改成只在該容器內加 icon */
div[data-testid="stSidebarNav"] > div:has(> span),
div[data-testid="stSidebarNav"] > div:has(> p){
  margin-top: 6px;
}

/* 群組標題文字：次大字（只影響群組標題行） */
div[data-testid="stSidebarNav"] > div:has(> span) > span,
div[data-testid="stSidebarNav"] > div:has(> p) > p{
  font-size: 20px !important;
  font-weight: 850 !important;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* ✅ 只在群組標題行前放一個 🚚（不會跑到其他行） */
div[data-testid="stSidebarNav"] > div:has(> span) > span::before,
div[data-testid="stSidebarNav"] > div:has(> p) > p::before{
  content: "🚚";
  font-size: 20px;
  margin-right: 2px;
}

/* 保險：絕對不要讓 a/button 的子元素出現 ::before icon */
div[data-testid="stSidebarNav"] li a *::before,
div[data-testid="stSidebarNav"] li button *::before{
  content: "" !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================
# Pages（依你目前檔名）
# =========================
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# =========================
# Navigation
# - 首頁：只有一個，不下拉
# - 進貨課：預設收合（不點不展開）
# =========================
pg = st.navigation(
    {
        "": [home_page],
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,
)

pg.run()
