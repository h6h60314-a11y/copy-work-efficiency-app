# app.py
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
section[data-testid="stSidebar"]{ padding-top: 10px; }

/* ✅ 新版 Streamlit：側欄容器與連結 testid */
section[data-testid="stSidebar"] [data-testid="stSidebarNavContainer"] a[data-testid="stSidebarNavLink"]{
  text-decoration: none !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavContainer"] a[data-testid="stSidebarNavLink"] *{
  font-size: 16px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavContainer"] li a[data-testid="stSidebarNavLink"]{
  padding-top: 8px !important;
  padding-bottom: 8px !important;
}

/* ✅ 首頁最大（新版結構一樣可吃到：第一個 nav link） */
section[data-testid="stSidebar"] [data-testid="stSidebarNavContainer"] ul > li:first-child a[data-testid="stSidebarNavLink"]{
  display:flex !important;
  align-items:center !important;
  justify-content:flex-start !important;
  gap: 6px !important;
  padding: 10px 12px !important;
  min-height: 48px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNavContainer"] ul > li:first-child a[data-testid="stSidebarNavLink"] *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.15 !important;
  white-space: nowrap !important;
  text-align: left !important;
}

/* 群組標題次大（群組標題不是 link，通常是 header/label 類型元素，這裡不強綁，避免跑版） */
</style>

<script>
(function () {
  // ✅ 只要 href 內含這些 key，就視為「群組首頁」要隱藏
  // 你的 DevTools 目前是 /~/+/outbound-home，所以用 outbound-home 就能命中
  const HIDE_KEYS = ["outbound-home", "inbound-home", "gt-kpi-home"];

  function shouldHide(href){
    if(!href) return false;
    return HIDE_KEYS.some(k => href.includes(k));
  }

  function hideLinks(){
    const sidebar = document.querySelector('section[data-testid="stSidebar"]');
    if(!sidebar) return;

    // ✅ 新版：stSidebarNavContainer / stSidebarNavLink
    const nav = sidebar.querySelector('[data-testid="stSidebarNavContainer"]');
    if(!nav) return;

    nav.querySelectorAll('a[data-testid="stSidebarNavLink"][href]').forEach(a => {
      const href = a.getAttribute("href") || "";
      if (shouldHide(href)) {
        const li = a.closest("li");
        if (li) li.style.display = "none";
        else a.style.display = "none";
      }
    });
  }

  // 反覆嘗試，因為 Streamlit 會重繪 sidebar
  function run(){
    hideLinks();
  }

  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => run());
  obs.observe(root, { childList: true, subtree: true });

  // 初次與延遲再跑一次（保險）
  run();
  setTimeout(run, 200);
  setTimeout(run, 800);
})();
</script>
""",
    unsafe_allow_html=True,
)

# ✅ 首頁
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

# ✅ 出貨課：第一個放「出貨課首頁」（會被隱藏）
outbound_home = st.Page(
    "pages/7_出貨課首頁.py",
    title="出貨課首頁",
    icon="📦",
    url_path="outbound-home",
)
transfer_diff_page = st.Page("pages/6_撥貨差異.py", title="撥貨差異", icon="📦")

# ✅ 進貨課：第一個放「進貨課首頁」（會被隱藏）
inbound_home = st.Page(
    "pages/8_進貨課首頁.py",
    title="進貨課首頁",
    icon="🚚",
    url_path="inbound-home",
)
qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# ✅ 大樹KPI：第一個放「大樹KPI首頁」（會被隱藏）
gt_kpi_home = st.Page(
    "pages/9_大樹KPI首頁.py",
    title="大樹KPI首頁",
    icon="📈",
    url_path="gt-kpi-home",
)
gt_inbound_receipt = st.Page("pages/10_進貨驗收量.py", title="進貨驗收量", icon="📥")

pg = st.navigation(
    {
        "": [home_page],
        "出貨課": [outbound_home, transfer_diff_page],
        "進貨課": [inbound_home, qc_page, putaway_page, pick_page, slot_page, diff_page],
        "大樹KPI": [gt_kpi_home, gt_inbound_receipt],
    },
    expanded=False,
)

pg.run()
