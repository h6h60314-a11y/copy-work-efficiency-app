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

/* ✅ 子選單固定回正常大小（避免被群組標題吃到） */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) ul a *{
  font-size: 16px !important; font-weight: 700 !important; line-height: 1.35 !important;
}

/* =========================================================
   ✅ 隱藏「每個群組的第一個子頁」（也就是課別首頁）
   這樣側欄只看到群組標題，不會重複出現「出貨課首頁 / 進貨課首頁」
   ========================================================= */
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul > li:has(ul) ul > li:first-child{
  display: none !important;
}
</style>

<script>
/* =========================================================
   ✅ 讓群組標題可點：點群組標題 -> 觸發該群組第一個子頁連結
   （即：出貨課/進貨課首頁）
   ========================================================= */
(function () {
  function bindGroupHeaderClick(){
    const navRoot = document.querySelector('section[data-testid="stSidebar"] [data-testid="stSidebarNav"] > ul');
    if(!navRoot) return;

    navRoot.querySelectorAll(':scope > li').forEach(li => {
      const subUl = li.querySelector(':scope > ul');
      if(!subUl) return;

      const firstLink = subUl.querySelector('a');
      if(!firstLink) return;

      // 找群組標題容器：li 的第一個 child（不是 ul）
      let header = null;
      for (const child of li.children){
        if (child.tagName && child.tagName.toLowerCase() !== 'ul'){ header = child; break; }
      }
      if(!header) return;

      header.style.cursor = 'pointer';
      header.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        // 直接觸發第一個子頁（即課別首頁）
        firstLink.click();
      }, { passive: false });
    });
  }

  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => bindGroupHeaderClick());
  obs.observe(root, { childList: true, subtree: true });

  bindGroupHeaderClick();
})();
</script>
""",
    unsafe_allow_html=True,
)

# =========================
# ✅ Pages
# =========================
home_page = st.Page("pages/0_首頁.py", title="首頁", icon="🏠", default=True)

# ✅ 出貨課（第一個是「出貨課首頁」：會被側欄隱藏，但群組標題點下去會進來）
outbound_home = st.Page("pages/7_出貨課首頁.py", title="出貨課首頁", icon="📦")
transfer_diff_page = st.Page("pages/1_撥貨差異.py", title="撥貨差異", icon="📦")

# ✅ 進貨課（第一個是「進貨課首頁」：會被側欄隱藏，但群組標題點下去會進來）
inbound_home = st.Page("pages/8_進貨課首頁.py", title="進貨課首頁", icon="🚚")
qc_page = st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅")
putaway_page = st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦")
pick_page = st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯")
slot_page = st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊")
diff_page = st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎")

pg = st.navigation(
    {
        "": [home_page],
        "出貨課": [outbound_home, transfer_diff_page],
        "進貨課": [inbound_home, qc_page, putaway_page, pick_page, slot_page, diff_page],
    },
    expanded=False,
)

pg.run()
