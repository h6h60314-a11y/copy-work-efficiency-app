# pages/7_出貨課首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 出貨課", page_icon="📦", layout="wide")
inject_logistics_theme()


def _route_by_query():
    qp = st.query_params
    raw = qp.get("page", "")

    if isinstance(raw, list):
        raw = raw[0] if raw else ""

    if not raw:
        return

    st.query_params.clear()
    st.switch_page(unquote(raw))


def _home_css_and_js():
    st.markdown(
        r"""
<style>
/* =========================================================
   ✅ 只作用在本頁（避免影響其它頁面）
   ========================================================= */
.dept-home a,
.dept-home a:visited{
  color: rgba(15, 23, 42, 0.92) !important;
  text-decoration: none !important;
}

/* ✅ 去除藍色 focus / 藍框（僅本區塊） */
.dept-home a:focus,
.dept-home a:focus-visible{
  outline: none !important;
  box-shadow: none !important;
}

/* =========================
   清單：緊湊版（• + icon + 可點標題 + 同行描述）
   ========================= */
.dept-home{ margin-top: 2px; }
.dept-home .home-list{ margin-top: 6px; }

.dept-home .home-row{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 10px 0;
}

.dept-home .home-left{
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  width: 34px;
  flex: 0 0 34px;
  margin-top: 2px;
}

.dept-home .home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 16px;
  line-height: 1;
}

.dept-home .home-ico{
  font-size: 16px;
  line-height: 1;
}

.dept-home .home-right{
  flex: 1 1 auto;
  line-height: 1.55;
}

.dept-home .home-link{
  display: inline;
  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900;
  font-size: 16px;
  line-height: 1.45;
  text-decoration: none !important;
  cursor: pointer;
}

.dept-home .home-link:hover{ opacity: 0.86; }

.dept-home .home-desc{
  display: inline;
  margin-left: 6px;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}

/* ✅ 把 markdown 預設上下空白縮小（只本區塊） */
.dept-home div[data-testid="stMarkdown"]{ margin: 0 !important; }
</style>

<script>
/* ✅ 同一視窗導頁（且避免重複綁定） */
(function () {
  function bindOnce() {
    document.querySelectorAll('.dept-home a.home-link').forEach(a => {
      if (a.dataset.bound === "1") return;
      a.dataset.bound = "1";
      a.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.assign(a.getAttribute('href'));
      }, { passive: false });
    });
  }

  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => bindOnce());
  obs.observe(root, { childList: true, subtree: true });
  bindOnce();
})();
</script>
""",
        unsafe_allow_html=True,
    )


def _nav_item(icon: str, title: str, page_path: str, desc: str):
    encoded = quote(page_path, safe="/_.-")
    st.markdown(
        f"""
<div class="home-row">
  <div class="home-left">
    <span class="home-bullet">•</span>
    <span class="home-ico">{icon}</span>
  </div>
  <div class="home-right">
    <a class="home-link" href="?page={encoded}" target="_self">{title}：</a>
    <span class="home-desc">{desc}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def main():
    _route_by_query()

    set_page("出貨課", icon="📦", subtitle="Outbound｜出貨相關模組入口")

    card_open("📦 出貨課模組")

    # ✅ wrapper scope，讓 CSS/JS 只影響本頁內容
    st.markdown('<div class="dept-home">', unsafe_allow_html=True)
    _home_css_and_js()

    st.markdown('<div class="home-list">', unsafe_allow_html=True)

    # ✅ 注意：你的 app.py 出貨課頁面是 pages/6_撥貨差異.py（不是 pages/1_撥貨差異.py）
    _nav_item(
        "📦",
        "撥貨差異",
        "pages/6_撥貨差異.py",
        "AllDIF/ALLACT 篩選 → 明細套巨集邏輯 → 儲位比對棚別 → 輸出差異明細",
    )

    # 之後出貨課項目就照這樣往下加：
    # _nav_item("📤","出貨作業效能","pages/XX_出貨作業效能.py","...")
    # _nav_item("🧾","包裝異常","pages/XX_包裝異常.py","...")
    # _nav_item("🚨","出貨異常","pages/XX_出貨異常.py","...")

    st.markdown("</div>", unsafe_allow_html=True)  # .home-list
    st.markdown("</div>", unsafe_allow_html=True)  # .dept-home

    card_close()


if __name__ == "__main__":
    main()
