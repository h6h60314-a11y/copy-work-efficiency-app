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
section[data-testid="stSidebar"]{ padding-top: 10px; }

/* ✅ 新版 Streamlit：側欄連結 */
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]{
  text-decoration: none !important;
}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] *{
  font-size: 16px !important;
  font-weight: 700 !important;
  line-height: 1.35 !important;
}

/* ✅ 首頁最大 */
section[data-testid="stSidebar"] ul > li:first-child a[data-testid="stSidebarNavLink"]{
  display:flex !important;
  align-items:center !important;
  justify-content:flex-start !important;
  gap:6px !important;
  padding:10px 12px !important;
  min-height:48px !important;
}
section[data-testid="stSidebar"] ul > li:first-child a[data-testid="stSidebarNavLink"] *{
  font-size:30px !important;
  font-weight:950 !important;
  line-height:1.15 !important;
  white-space:nowrap !important;
  text-align:left !important;
}

/* ✅✅ 備援：直接用 CSS :has 隱藏含特定 href 的 li（Chrome OK） */
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="outbound-home"]){ display:none !important; }
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="inbound-home"]){  display:none !important; }
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="gt-kpi-home"]){    display:none !important; }
</style>

<script>
(function () {
  const HIDE_KEYS = ["outbound-home", "inbound-home", "gt-kpi-home"];

  function shouldHide(href){
    if(!href) return false;
    return HIDE_KEYS.some(k => href.includes(k));
  }

  function hideGroupHomeLinks(){
    const sidebar = document.querySelector('section[data-testid="stSidebar"]');
    if(!sidebar) return;

    // ✅ 直接掃整個 sidebar 內所有 nav link（不再依賴 container 結構）
    const links = sidebar.querySelectorAll('a[data-testid="stSidebarNavLink"][href]');
    links.forEach(a => {
      const href = a.getAttribute("href") || a.href || "";
      if (shouldHide(href)) {
        const li = a.closest("li");
        if (li) li.style.display = "none";
        a.style.display = "none";
      }
    });
  }

  function run(){
    hideGroupHomeLinks();
  }

  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => run());
  obs.observe(root, { childList: true, subtree: true });

  // 多跑幾次，保證 Streamlit 重繪也能吃到
  run();
  setTimeout(run, 50);
  setTimeout(run, 200);
  setTimeout(run, 800);
  setTimeout(run, 2000);
})();
</script>
""",
    unsafe_allow_html=True,
)

# ✅ 首頁
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

# ✅ 出貨課（第一個是群組首頁：要隱藏）
outbound_home = st.Page("pages/7_出貨課首頁.py", title="出貨課首頁", icon="📦", url_path="outbound-home")
transfer_diff_page = st.Page("pages/6_撥貨差異.py", title="撥貨差異", icon="📦")

# ✅ 進貨課（第一個是群組首頁：要隱藏）
inbound_home = st.Page("pages/8_進貨課首頁.py", title="進貨課首頁", icon="🚚", url_path="inbound-home")
qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# ✅ 大樹KPI（第一個是群組首頁：要隱藏）
gt_kpi_home = st.Page("pages/9_大樹KPI首頁.py", title="大樹KPI首頁", icon="📈", url_path="gt-kpi-home")
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
