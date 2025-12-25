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
/* =========================
   Sidebar base
   ========================= */
section[data-testid="stSidebar"]{
  padding-top: 10px;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI",
               "Noto Sans TC", "Microsoft JhengHei", Arial, sans-serif;
}

/* ✅ 新版 Streamlit：側欄連結 */
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]{
  text-decoration: none !important;
}

/* ✅ 文字：更舒服、直觀 */
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] *{
  font-size: 15.5px !important;
  font-weight: 650 !important;
  line-height: 1.55 !important;
  letter-spacing: .2px !important;
}

/* ✅ 每個項目上下距離 */
section[data-testid="stSidebar"] li a[data-testid="stSidebarNavLink"]{
  padding-top: 6px !important;
  padding-bottom: 6px !important;
}

/* ✅ 首頁最大（不誇張） */
section[data-testid="stSidebar"] ul > li:first-child a[data-testid="stSidebarNavLink"]{
  display:flex !important;
  align-items:center !important;
  justify-content:flex-start !important;
  gap:8px !important;
  padding: 10px 12px !important;
  min-height:48px !important;
  border-radius: 12px !important;
}
section[data-testid="stSidebar"] ul > li:first-child a[data-testid="stSidebarNavLink"] *{
  font-size: 26px !important;
  font-weight: 900 !important;
  line-height: 1.15 !important;
  white-space: nowrap !important;
  text-align: left !important;
  letter-spacing: .3px !important;
}

/* ✅ 群組標題（出貨課/進貨課/大樹KPI） */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h2,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h3,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h4{
  font-size: 13.5px !important;
  font-weight: 850 !important;
  color: rgba(15,23,42,.72) !important;
  letter-spacing: .9px !important;
  margin: 14px 0 6px !important;
}

/* ✅ icon 與字距離一致 */
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]{
  gap: 8px !important;
}

/* =========================================================
   ✅✅ 隱藏「群組首頁頁」：CSS 版本（href + label 雙保險）
   ========================================================= */

/* 1) 用 href url_path 關鍵字 */
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="outbound-home"]){ display:none !important; }
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="inbound-home"]){  display:none !important; }
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="gt-kpi-home"]){    display:none !important; }

/* 2) 用 label 文字（你 DevTools 看到的 span[label="xxx"]） */
section[data-testid="stSidebar"] li:has(span[label="出貨課首頁"]){ display:none !important; }
section[data-testid="stSidebar"] li:has(span[label="進貨課首頁"]){ display:none !important; }
section[data-testid="stSidebar"] li:has(span[label="大樹KPI首頁"]){ display:none !important; }
</style>

<script>
(function () {
  const HIDE_LABELS = ["出貨課首頁", "進貨課首頁", "大樹KPI首頁"];
  const HIDE_KEYS   = ["outbound-home", "inbound-home", "gt-kpi-home"];

  function hideByHrefAndLabel(){
    const sidebar = document.querySelector('section[data-testid="stSidebar"]');
    if(!sidebar) return;

    // ✅ 找所有 nav links
    const links = sidebar.querySelectorAll('a[data-testid="stSidebarNavLink"]');

    links.forEach(a => {
      const href = (a.getAttribute("href") || a.href || "");
      const labelSpan = a.querySelector('span[label]');
      const label = labelSpan ? (labelSpan.getAttribute("label") || "") : "";

      const hitHref  = HIDE_KEYS.some(k => href.includes(k));
      const hitLabel = HIDE_LABELS.includes(label);

      if(hitHref || hitLabel){
        const li = a.closest("li");
        if(li) li.style.display = "none";
        a.style.display = "none";
      }
    });
  }

  function run(){ hideByHrefAndLabel(); }

  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => run());
  obs.observe(root, { childList: true, subtree: true });

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
outbound_home = st.Page(
    "pages/7_出貨課首頁.py",
    title="出貨課首頁",
    icon="📦",
    url_path="outbound-home",
)
transfer_diff_page = st.Page("pages/6_撥貨差異.py", title="撥貨差異", icon="📦")

# ✅ 進貨課（第一個是群組首頁：要隱藏）
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

# ✅ 大樹KPI（第一個是群組首頁：要隱藏）
gt_kpi_home = st.Page(
    "pages/9_大樹KPI首頁.py",
    title="大樹KPI首頁",
    icon="📈",
    url_path="gt-kpi-home",
)
gt_inbound_receipt = st.Page("pages/10_進貨驗收量.py", title="進貨驗收量", icon="📥")

# ✅ 新模組：出貨應出量分析（檔名你指定：pages/11_出貨訂單應出量分析.py）
gt_ship_units = st.Page(
    "pages/11_出貨訂單應出量分析.py",
    title="出貨訂單應出量分析",
    icon="📦",
)

pg = st.navigation(
    {
        "": [home_page],
        "出貨課": [outbound_home, transfer_diff_page],
        "進貨課": [inbound_home, qc_page, putaway_page, pick_page, slot_page, diff_page],
        "大樹KPI": [gt_kpi_home, gt_inbound_receipt, gt_ship_units],
    },
    expanded=False,
)

pg.run()
