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
# Sidebar UI: 字體層級 + 進貨課標題圖示
# - 首頁字體最大
# - 進貨課標題次大
# - 子項目維持正常大小
# =========================================
st.markdown(
    """
    <style>
    /* Sidebar padding */
    section[data-testid="stSidebar"]{
        padding-top: 8px;
    }

    /* Sidebar 群組標題（例如：進貨課） */
    section[data-testid="stSidebar"] h2{
        font-size: 20px !important;   /* 次大 */
        font-weight: 850 !important;
        margin-top: 18px !important;
        margin-bottom: 6px !important;
        display: flex;
        align-items: center;
        gap: 6px;
        letter-spacing: 0.5px;
    }

    /* 群組標題前加圖示（📦） */
    section[data-testid="stSidebar"] h2::before{
        content: "📦";
        font-size: 22px;
        margin-right: 4px;
    }

    /* Sidebar 所有頁面連結：維持一致、不要太大 */
    section[data-testid="stSidebar"] a{
        font-size: 15px !important;
        font-weight: 650 !important;
        text-decoration: none !important;
    }

    /* 首頁（Home）字體最大：用 href 內含「首頁」來鎖定 */
    section[data-testid="stSidebar"] a[href*="首頁"]{
        font-size: 22px !important;   /* 最大 */
        font-weight: 900 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================
# Pages
# =========================================
home_page = st.Page(
    "pages/0_首頁.py",
    title="首頁",
    icon="🏠",
    default=True,
)

qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page(
    "pages/5_揀貨差異代庫存.py",
    title="揀貨差異代庫存",
    icon="🔎",
)

# =========================================
# Navigation
# - 首頁只顯示一個（不出現群組下拉）：放到 "" 群組
# - 進貨課預設收合：expanded=False
# =========================================
pg = st.navigation(
    {
        "": [home_page],  # ✅ 不顯示群組標題 → 只剩一個「首頁」
        "進貨課": [qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,  # ✅ 預設收合（不點進貨課不展開子項）
)

pg.run()
