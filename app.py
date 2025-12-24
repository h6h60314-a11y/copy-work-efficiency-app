import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",  # 依你的專案路徑調整
    layout="wide",
)

# =========================
# Sidebar CSS（穩定：用 href 鎖首頁，用 aria-expanded 鎖群組標題）
# =========================
st.markdown(
    r"""
<style>
/* ========== Sidebar base ========== */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* 讓導覽看起來更像條列 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul{
  margin-top: 6px !important;
}

/* 所有導覽項目：基準字體 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] button{
  text-decoration: none !important;
}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a *{
  font-size: 16px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
}

/* 讓每一列更好點 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li a{
  padding-top: 8px !important;
  padding-bottom: 8px !important;
}

/* ========== ✅ 群組標題：🚚 進貨課（字體次大） ========== */
/*
  Streamlit 群組標題通常會是「可展開/收合」的按鈕，會帶 aria-expanded 屬性
  這樣可以精準鎖定，不會影響到一般連結
*/
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] button[aria-expanded] *{
  font-size: 22px !important;
  font-weight: 900 !important;
  line-height: 1.2 !important;
}

/* 群組標題上下留白，避免擠在一起 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] button[aria-expanded]{
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* ========== ✅ 首頁（字最大）：用 href 精準鎖 0_首頁 ========== */
/*
  Streamlit 多頁的連結 href 常見會帶 pages/0_首頁.py 或 URL encoded 的 0_%E9%A6%96%E9%A0%81
  這裡兩個都寫，確保命中
*/
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="pages/0_首頁.py"] *,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="0_%E9%A6%96%E9%A0%81"] *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.12 !important;
}

/* 首頁那列的 icon 也放大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="pages/0_首頁.py"] svg,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="0_%E9%A6%96%E9%A0%81"] svg{
  width: 24px !important;
  height: 24px !important;
  transform: translateY(2px);
}

/* 首頁那列給更多留白，視覺更像主入口 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="pages/0_首頁.py"],
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[href*="0_%E9%A6%96%E9%A0%81"]{
  padding-top: 12px !important;
  padding-bottom: 12px !important;
}

/* （可選）目前選中的頁面，稍微加強辨識 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"]{
  border-radius: 10px;
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

pg = st.navigation(
    {
        "": [home_page],
        "🚚 進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,  # 不點不展開
)

pg.run()
