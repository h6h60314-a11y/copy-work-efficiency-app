import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",  # 依你的專案路徑調整
    layout="wide",
)

# =========================
# Sidebar CSS（精準命中 + 不互相覆蓋）
# =========================
st.markdown(
    """
<style>
/* ---- Sidebar base ---- */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* 所有導覽項目：正常大小 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] button{
  text-decoration: none !important;
}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a *,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] button *{
  font-size: 15px !important;
  font-weight: 650 !important;
  line-height: 1.35 !important;
}

/* ✅ 首頁：只鎖「第一個 item 的文字容器」放大 + 修正高度，避免重疊 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child a,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child button{
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child a *,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child button *{
  font-size: 26px !important;
  font-weight: 900 !important;
  line-height: 1.15 !important;   /* ✅ 防止字擠壓 */
}

/* ✅ 首頁 icon 的尺寸也一起放大，並置中 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li:first-child svg{
  width: 22px !important;
  height: 22px !important;
  transform: translateY(2px);
}

/* ✅ 進貨課：只鎖「群組標題」那一行
   Streamlit 群組標題通常是：nav 內部的 section header（不是 a/button）
   這個 selector 會抓到 sidebar nav 中，出現在 li 列表之前的那個標題文字 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > div:has(> ul) > div:first-child *{
  font-size: 20px !important;
  font-weight: 850 !important;
  line-height: 1.2 !important;
}

/* ✅ 如果你的版本群組標題不是上面那種結構，再加一個 fallback：
   抓 sidebar nav 裡「不是連結的純文字行」(p/span) 並放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] p,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] span{
  font-size: 20px;
  font-weight: 850;
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

pg = st.navigation(
    {
        "": [home_page],
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,  # ✅ 不點不展開
)

pg.run()
