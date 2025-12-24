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

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a{ text-decoration: none !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a *{
  font-size: 16px !important; font-weight: 700 !important; line-height: 1.35 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li a{
  padding-top: 8px !important; padding-bottom: 8px !important;
}

/* 首頁最大 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a{
  display:flex !important; align-items:center !important; justify-content:flex-start !important;
  gap:6px !important; padding:10px 12px !important; min-height:48px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  font-size:30px !important; font-weight:950 !important; line-height:1.15 !important;
  white-space:nowrap !important; text-align:left !important;
}

/* 群組標題次大（大多數情況 Streamlit 會是 li > div:first-child） */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li{ margin-top: 6px !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li > div:first-child *{
  font-size: 22px !important; font-weight: 900 !important; line-height: 1.2 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li > div:first-child{
  padding-top: 10px !important; padding-bottom: 10px !important;
}
</style>

<script>
(function () {
  // ✅ 只隱藏這三個「群組首頁」的 url_path（精準、不誤傷）
  const HIDE_URL_KEYS = ["outbound-home", "inbound-home", "gt-kpi-home"];

  function shouldHideHref(href){
    if(!href) return false;
    // 可能是 "/outbound-home"、"outbound-home"、"./outbound-home"、或帶 query
    return HIDE_URL_KEYS.some(k => href.includes(k));
  }

  function hideGroupHomeLinks(){
    const nav = document.querySelector('section[data-testid="stSidebar"] [data-testid="stSidebarNav"]');
    if(!nav) return;

    nav.querySelectorAll('a[href]').forEach(a => {
      const href = a.getAttribute('href') || "";
      if (shouldHideHref(href)) {
        const li = a.closest("li");
        if (li) li.style.display = "none";
        else a.style.display = "none";
      }
    });
  }

  function bindGroupHeaderClick(){
    const navRoot = document.querySelector('section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul');
    if(!navRoot) return;

    navRoot.querySelectorAll(':scope > li').forEach(li => {
      const sub = li.querySelector(':scope > ul');
      if(!sub) return;

      // ✅ 找到「群組首頁」那個 link（即 outbound-home / inbound-home / gt-kpi-home）
      const links = Array.from(sub.querySelectorAll('a[href]'));
      const homeLink = links.find(a => shouldHideHref(a.getAttribute('href') || "")) || links[0];
      if(!homeLink) return;

      const header = li.querySelector(':scope > div:first-child');
      if(!header) return;

      if (header.dataset.boundGroupClick === "1") return;
      header.dataset.boundGroupClick = "1";
      header.style.cursor = "pointer";

      header.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        // 即使 homeLink 被隱藏，HTMLElement.click() 仍可觸發導頁
        homeLink.click();
      }, { passive: false });
    });
  }

  function runAll(){
    bindGroupHeaderClick();
    hideGroupHomeLinks();
  }

  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => runAll());
  obs.observe(root, { childList: true, subtree: true });
  runAll();
})();
</script>
""",
    unsafe_allow_html=True,
)

# ✅ 首頁
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

# ✅ 出貨課（群組首頁：會被隱藏，但群組標題點下去會進這頁）
outbound_home = st.Page("pages/7_出貨課首頁.py", title="出貨課首頁", icon="📦", url_path="outbound-home")
transfer_diff_page = st.Page("pages/6_撥貨差異.py", title="撥貨差異", icon="📦")

# ✅ 進貨課（群組首頁：會被隱藏）
inbound_home = st.Page("pages/8_進貨課首頁.py", title="進貨課首頁", icon="🚚", url_path="inbound-home")
qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# ✅ 大樹KPI（群組首頁：會被隱藏）
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
