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
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  gap: 6px !important;
  padding: 10px 12px !important;
  min-height: 48px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:first-child a *{
  font-size: 30px !important;
  font-weight: 950 !important;
  line-height: 1.15 !important;
  white-space: nowrap !important;
  text-align: left !important;
}

/* 群組標題次大（支援沒有 :has 也能套到大部分元素） */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li{
  margin-top: 6px !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li > div:first-child *{
  font-size: 22px !important;
  font-weight: 900 !important;
  line-height: 1.2 !important;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li > div:first-child{
  padding-top: 10px !important;
  padding-bottom: 10px !important;
}

/* ✅✅✅ 關鍵：隱藏「每個群組的第一個子項」（你的 XX首頁 都是放第一個） */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul ul > li:first-child{
  display: none !important;
}
</style>

<script>
/* ✅ 群組標題可點：點群組標題 -> 開啟該群組第一個子頁（即：群組首頁） */
(function () {
  function bindGroupHeaderClick(){
    const navRoot = document.querySelector('section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul');
    if(!navRoot) return;

    navRoot.querySelectorAll(':scope > li').forEach(li => {
      const subUl = li.querySelector(':scope > ul');
      if(!subUl) return;

      const firstLink = subUl.querySelector('a'); // 第一個子頁（雖然被隱藏，但仍存在）
      if(!firstLink) return;

      // 群組標題：li 的第一個 div（Streamlit 常見結構）
      const header = li.querySelector(':scope > div:first-child');
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

  function bindAll(){ bindGroupHeaderClick(); }

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

# ✅ 出貨課（第一個放「出貨課首頁」→ 會被隱藏，但群組標題點下去會進這頁）
outbound_home = st.Page("pages/7_出貨課首頁.py", title="出貨課首頁", icon="📦", url_path="outbound-home")
transfer_diff_page = st.Page("pages/6_撥貨差異.py", title="撥貨差異", icon="📦")

# ✅ 進貨課
inbound_home = st.Page("pages/8_進貨課首頁.py", title="進貨課首頁", icon="🚚", url_path="inbound-home")
qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

# ✅ 大樹KPI
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
