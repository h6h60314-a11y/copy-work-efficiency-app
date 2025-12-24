# pages/6_出貨課首頁.py
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
/* =========================
   ✅ 去除藍色底 / 藍色框（課別首頁覆蓋）
   ========================= */
section[data-testid="stAppViewContainer"] a,
section[data-testid="stAppViewContainer"] a:visited{
  color: rgba(15, 23, 42, 0.92) !important;
  text-decoration: none !important;
}
section[data-testid="stAppViewContainer"] a,
section[data-testid="stAppViewContainer"] button{
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  outline: none !important;
}
section[data-testid="stAppViewContainer"] a:focus,
section[data-testid="stAppViewContainer"] a:focus-visible,
section[data-testid="stAppViewContainer"] button:focus,
section[data-testid="stAppViewContainer"] button:focus-visible{
  outline: none !important;
  box-shadow: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]{
  background: rgba(255,255,255,0.98) !important;
  border-color: rgba(15, 23, 42, 0.12) !important;
  box-shadow: none !important;
}

/* =========================
   清單：緊湊版（• + icon + 可點標題 + 同行描述）
   ========================= */
.home-list{ margin-top: 6px; }
.home-row{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 10px 0;
}
.home-left{
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  width: 34px;
  flex: 0 0 34px;
  margin-top: 2px;
}
.home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 16px;
  line-height: 1;
}
.home-ico{
  font-size: 16px;
  line-height: 1;
}
.home-right{
  flex: 1 1 auto;
  line-height: 1.55;
}
.home-link{
  display: inline;
  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900;
  font-size: 16px;
  line-height: 1.45;
  text-decoration: none !important;
  cursor: pointer;
}
.home-link:hover{ opacity: 0.86; }
.home-desc{
  display: inline;
  margin-left: 6px;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}
div[data-testid="stMarkdown"]{ margin: 0 !important; }
</style>

<script>
/* ✅ 同一視窗導頁：攔截 .home-link，改用 location.assign */
(function () {
  function bind() {
    document.querySelectorAll('a.home-link').forEach(a => {
      a.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.assign(a.getAttribute('href'));
      }, { passive: false });
    });
  }
  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => bind());
  obs.observe(root, { childList: true, subtree: true });
  bind();
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
    _home_css_and_js()

    st.markdown('<div class="home-list">', unsafe_allow_html=True)

    _nav_item(
        "📦",
        "撥貨差異",
        "pages/1_撥貨差異.py",
        "AllDIF/ALLACT 篩選 → 明細套巨集邏輯 → 儲位比對棚別 → 輸出差異明細",
    )

    # 之後出貨課項目就照這樣往下加：
    # _nav_item("📤","出貨作業效能","pages/XX_出貨作業效能.py","...")

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()


if __name__ == "__main__":
    main()
