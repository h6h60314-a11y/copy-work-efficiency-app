import streamlit as st

# =========================================
# App Config
# =========================================
st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",
    layout="wide",
)

# =========================================
# Sidebar CSS：確保「首頁」與「進貨課」真的放大
# - Streamlit 不同版本 DOM 可能不同：用多組 selector 增強命中率
# =========================================
st.markdown(
    r"""
<style>
/* Sidebar padding */
section[data-testid="stSidebar"]{
  padding-top: 10px;
}

/* -------------------------------
   子頁：預設字級
-------------------------------- */
section[data-testid="stSidebar"] a span,
section[data-testid="stSidebar"] a p{
  font-size: 15px !important;
  font-weight: 650 !important;
  text-decoration: none !important;
}

/* -------------------------------
   首頁：最大字（多組 selector）
   - 可能出現在 href 包含「首頁」或 URL encode
-------------------------------- */
section[data-testid="stSidebar"] a[href*="首頁"] span,
section[data-testid="stSidebar"] a[href*="%E9%A6%96%E9%A0%81"] span,
section[data-testid="stSidebar"] a[href*="0_%E9%A6%96%E9%A0%81"] span,
section[data-testid="stSidebar"] a[href*="0_首頁"] span{
  font-size: 24px !important;
  font-weight: 900 !important;
}

/* -------------------------------
   群組標題：進貨課（次大 + 🚚）
   目標：Sidebar Nav 裡「不是 link」的那一行（群組標題）
   Streamlit 版本不同，提供多種命中方式
-------------------------------- */

/* 版本A：常見結構（群組標題不是 a） */
div[data-testid="stSidebarNav"] span:not(a span),
section[data-testid="stSidebarNav"] span:not(a span){
  font-size: 20px !important;
  font-weight: 850 !important;
  display: flex;
  align-items: center;
  letter-spacing: 0.5px;
}

/* 避免把所有 span 都加 icon：只對「群組標題」加（更精準） */
div[data-testid="stSidebarNav"] > div > div > div > span::before,
section[data-testid="stSidebarNav"] > div > div > div > span::before{
  content: "🚚 ";
  font-size: 22px;
  margin-right: 4px;
}

/* 版本B：若你的 Streamlit 結構不同（備援：只影響群組標題區塊） */
div[data-testid="stSidebarNav"] > div > div > span::before,
section[data-testid="stSidebarNav"] > div > div > span::before{
  content: "🚚 ";
  font-size: 22px;
  margin-right: 4px;
}
div[data-testid="stSidebarNav"] > div > div > span,
section[data-testid="stSidebarNav"] > div > div > span{
  font-size: 20px !important;
  font-weight: 850 !important;
  display: flex;
  align-items: center;
  letter-spacing: 0.5px;
}

/* 如果 icon 出現到子頁：把 a 內的 ::before 清掉 */
section[data-testid="stSidebar"] a span::before,
section[data-testid="stSidebar"] a p::before{
  content: "" !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================
# Pages（依你目前的檔名）
# =========================================
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# =========================================
# Navigation
# - "" 群組：只放首頁（不顯示群組標題 → 不會有下拉）
# - "進貨課" 群組：預設收合 expanded=False（不點不展開）
# =========================================
pg = st.navigation(
    {
        "": [home_page],  # ✅ 首頁只有一個，不出現群組下拉
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,  # ✅ 進貨課預設收合
)

pg.run()
