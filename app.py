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

/* ===== 子項：連結固定大小 ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a{ text-decoration: none !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a *{
  font-size: 16px !important; font-weight: 700 !important; line-height: 1.35 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] li a{
  padding-top: 8px !important; padding-bottom: 8px !important;
}

/* ===== 首頁最大 ===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a{
  display: flex !important; align-items: center !important; justify-content: flex-start !important;
  gap: 6px !important; padding: 10px 12px !important; min-height: 48px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  font-size: 30px !important; font-weight: 950 !important; line-height: 1.15 !important;
  white-space: nowrap !important; text-align: left !important;
}

/* ===== 群組標題次大（li 底下有 ul）===== */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul){ margin-top: 6px !important; }
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul) *{
  font-size: 22px !important; font-weight: 900 !important; line-height: 1.2 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) > :not(ul){
  padding-top: 10px !important; padding-bottom: 10px !important;
}

/* ✅ 子選單固定回正常大小 */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) ul a *{
  font-size: 16px !important; font-weight: 700 !important; line-height: 1.35 !important;
}
</style>

<script>
/* =========================================================
   ✅ 隱藏「群組首頁子項」：出貨課首頁 / 進貨課首頁 / 大樹KPI首頁
      - 優先用 url_path 精準比對（最穩）
      - 再用文字比對當備援
   ✅ 群組標題可點：點群組標題 -> 開啟該群組第一個子頁
   ========================================================= */
(function () {

  // 你在 st.Page(..., url_path="xxx") 設的值
  const HIDE_URLPATHS = ["outbound-home", "inbound-home", "gt-kpi-home"];

  // 備援：萬一 href 抓不到，就用文字隱藏
  const HIDE_TITLES = ["出貨課首頁", "進貨課首頁", "大樹KPI首頁"];

  function shouldHideLink(a){
    const href = (a.getAttribute("href") || "");
    // 精準：包含 /outbound-home 或 ?outbound-home 這類
    if (HIDE_URLPATHS.some(p => href.includes("/" + p) || href.includes(p))) return true;

    const txt = (a.textContent || "").replace(/\s+/g, "").trim();
    if (txt && HIDE_TITLES.some(t => txt.includes(t))) return true;

    return false;
  }

  function hideHomeItems(){
    const nav = document.querySelector('section[data-testid="stSidebar"] [data-testid="stSidebarNav"]');
    if(!nav) return;

    nav.querySelectorAll("a").forEach(a => {
      if (!shouldHideLink(a)) return;

      const li = a.closest("li");
      if (li) li.style.display = "none";
      else a.style.display = "none";
    });
  }

  function bindGroupHeaderClick(){
    const navRoot = document.querySelector('section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul');
    if(!navRoot) return;

    navRoot.querySelectorAll(':scope > li').forEach(li => {
      const subUl = li.querySelector(':scope > ul');
      if(!subUl) return;

      // 群組內第一個子頁（即使被隱藏，click 仍能導頁）
      const firstLink = subUl.querySelector('a');
      if(!firstLink) return;

      // 群組標題：li 的第一個非 ul 子節點
      let header = null;
      for (const child of Array.from(li.children)) {
        if (child.tagName && child.tagName.toLowerCase() !== 'ul') { header = child; break; }
      }
      if(!header) return;

      if (header.dataset.boundGroupClick === "1") return;
      header.dataset.boundGroupClick = "1";

      header.style.cursor = "pointer";
      header.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        firstLink.click();
      }, { passive: false });
    });
  }

  function bindAll(){
    hideHomeItems();
    bindGroupHeaderClick();
  }

  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => bindAll());
  obs.observe(root, { childList: true, subtree: true });
  bindAll();

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

# ✅ 進貨課（群組首頁：會被隱藏，但群組標題點下去會進這頁）
inbound_home = st.Page("pages/8_進貨課首頁.py", title="進貨課首頁", icon="🚚", url_path="inbound-home")
qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# ✅ 大樹KPI（群組首頁：會被隱藏，但群組標題點下去會進這頁）
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
