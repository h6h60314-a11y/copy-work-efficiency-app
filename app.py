import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",  # 依你的專案路徑調整
    layout="wide",
)

# =========================
# Sidebar CSS（穩定版：不加圖示，只放大指定文字）
# =========================
st.markdown(
    """
<style>
/* ---- Sidebar base ---- */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* 預設：所有 nav 項目字級 */
div[data-testid="stSidebarNav"] a,
div[data-testid="stSidebarNav"] button{
  text-decoration: none !important;
}
div[data-testid="stSidebarNav"] a *,
div[data-testid="stSidebarNav"] button *{
  font-size: 15px !important;
  font-weight: 650 !important;
  line-height: 1.25 !important;
}

/* ✅ 首頁：最大字（鎖第一個 nav item） */
div[data-testid="stSidebarNav"] li:first-child a *,
div[data-testid="stSidebarNav"] li:first-child button *{
  font-size: 26px !important;
  font-weight: 900 !important;
}

/* ✅ 進貨課：次大字（鎖「群組標題」那一行）
   Streamlit 群組標題通常不是 a/button，因此這裡只放大非 a/button 的直接文字容器 */
div[data-testid="stSidebarNav"] :is(h1,h2,h3,h4,p,span,div){
  /* 先全部還原，避免誤傷 */
  font-size: inherit;
  font-weight: inherit;
}

/* 只在 SidebarNav 區塊內，找「看起來像群組標題」的文字行：
   - 通常會出現在 a/button 列表之前
   - 且自身不是 a/button
   這邊用：nav 區塊裡「不是 link/button 的文字行」放大 */
div[data-testid="stSidebarNav"] > div > :is(p,span,div,h1,h2,h3,h4){
  font-size: 20px !important;
  font-weight: 850 !important;
  letter-spacing: .5px;
}

/* ✅ 保險：把子項目的字級固定回 15（避免被上面影響） */
div[data-testid="stSidebarNav"] li a *,
div[data-testid="stSidebarNav"] li button *{
  font-size: 15px !important;
  font-weight: 650 !important;
}

/* ✅ 再保險：首頁最大字要覆蓋回來 */
div[data-testid="stSidebarNav"] li:first-child a *,
div[data-testid="stSidebarNav"] li:first-child button *{
  font-size: 26px !important;
  font-weight: 900 !important;
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
# - 首頁只有一個
# - 進貨課預設收合（不點不展開）
# =========================
pg = st.navigation(
    {
        "": [home_page],
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,
)

pg.run()
