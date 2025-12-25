# app.py
import os
import streamlit as st

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",
    layout="wide",
)

st.markdown(
    r"""
<style>
section[data-testid="stSidebar"]{
  padding-top: 10px;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI",
               "Noto Sans TC", "Microsoft JhengHei", Arial, sans-serif;
}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]{
  text-decoration: none !important;
}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"] *{
  font-size: 15.5px !important;
  font-weight: 650 !important;
  line-height: 1.55 !important;
  letter-spacing: .2px !important;
}
section[data-testid="stSidebar"] li a[data-testid="stSidebarNavLink"]{
  padding-top: 6px !important;
  padding-bottom: 6px !important;
}
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
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h2,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h3,
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] h4{
  font-size: 13.5px !important;
  font-weight: 850 !important;
  color: rgba(15,23,42,.72) !important;
  letter-spacing: .9px !important;
  margin: 14px 0 6px !important;
}
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"]{
  gap: 8px !important;
}

/* 隱藏群組首頁 */
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="outbound-home"]){ display:none !important; }
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="inbound-home"]){  display:none !important; }
section[data-testid="stSidebar"] li:has(a[data-testid="stSidebarNavLink"][href*="gt-kpi-home"]){    display:none !important; }
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

  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => hideByHrefAndLabel());
  obs.observe(root, { childList: true, subtree: true });

  hideByHrefAndLabel();
  setTimeout(hideByHrefAndLabel, 50);
  setTimeout(hideByHrefAndLabel, 200);
  setTimeout(hideByHrefAndLabel, 800);
  setTimeout(hideByHrefAndLabel, 2000);
})();
</script>
""",
    unsafe_allow_html=True,
)


def page_if_exists(path: str, title: str, icon: str, **kwargs):
    if not os.path.exists(path):
        return None
    return st.Page(path, title=title, icon=icon, **kwargs)


# ✅ 首頁
home_page = page_if_exists("app_pages/0_首頁.py", "首頁", "🏠", default=True, url_path="home")

# ✅ 出貨課（群組首頁：要隱藏）
outbound_home = page_if_exists("app_pages/7_出貨課首頁.py", "出貨課首頁", "📦", url_path="outbound-home")
transfer_diff_page = page_if_exists("app_pages/6_撥貨差異.py", "撥貨差異", "📦", url_path="outbound-transfer-diff")

# ✅ 進貨課（群組首頁：要隱藏）
inbound_home = page_if_exists("app_pages/8_進貨課首頁.py", "進貨課首頁", "🚚", url_path="inbound-home")
qc_page = page_if_exists("app_pages/1_驗收作業效能.py", "驗收作業效能", "✅", url_path="inbound-qc")
putaway_page = page_if_exists("app_pages/2_上架作業效能.py", "上架作業效能", "📦", url_path="inbound-putaway")
pick_page = page_if_exists("app_pages/3_總揀作業效能.py", "總揀作業效能", "🎯", url_path="inbound-pick")
slot_page = page_if_exists("app_pages/4_儲位使用率.py", "儲位使用率", "🧊", url_path="inbound-slot-util")
diff_page = page_if_exists("app_pages/5_揀貨差異代庫存.py", "揀貨差異代庫存", "🔎", url_path="inbound-pick-diff")

# ✅ 大樹KPI（群組首頁：要隱藏）
gt_kpi_home = page_if_exists("app_pages/9_大樹KPI首頁.py", "大樹KPI首頁", "📈", url_path="gt-kpi-home")
gt_inbound_receipt = page_if_exists("app_pages/10_進貨驗收量.py", "進貨驗收量", "📥", url_path="gt-inbound-receipt")
gt_ship_should = page_if_exists("app_pages/11_庫存訂單應出量分析.py", "庫存訂單應出量分析", "📦", url_path="gt-ship-should")
gt_xdock = page_if_exists("app_pages/12_越庫訂單分析.py", "越庫訂單分析", "🧾", url_path="gt-xdock")
gt_ship_actual = page_if_exists("app_pages/13_庫存訂單實出量分析.py", "庫存訂單實出量分析", "🚚", url_path="gt-ship-actual")
gt_putaway_daily = page_if_exists("app_pages/14_每日上架分析.py", "每日上架分析", "📦", url_path="gt-putaway-daily")
gt_inv_accuracy = page_if_exists("app_pages/15_庫存盤點正確率.py", "庫存盤點正確率", "🎯", url_path="gt-inv-accuracy")
gt_store_arrival_abn = page_if_exists("app_pages/16_門市到貨異常率.py", "門市到貨異常率", "🏪", url_path="gt-store-arrival-abn")
gt_daily_attendance = page_if_exists("app_pages/17_每日出勤工時分析.py", "每日出勤工時分析", "🕒", url_path="gt-daily-attendance")

# ✅ 18_儲位使用率（KPI 入口）
slot_util_page = page_if_exists(
    "pages/18_各類儲區使用率.py",
    "各類儲區使用率",
    "🧊",
    url_path="slot-zone-util-18"
)

pg = st.navigation(
    {
        "": [p for p in [home_page] if p],
        "出貨課": [p for p in [outbound_home, transfer_diff_page] if p],
        "進貨課": [p for p in [inbound_home, qc_page, putaway_page, pick_page, slot_page, diff_page] if p],
        "大樹KPI": [p for p in [
            gt_kpi_home, gt_inbound_receipt, gt_ship_should, gt_xdock, gt_ship_actual,
            gt_putaway_daily, gt_inv_accuracy, gt_store_arrival_abn, gt_daily_attendance,
            slot_util_page
        ] if p],
    },
    expanded=False,
)

pg.run()

