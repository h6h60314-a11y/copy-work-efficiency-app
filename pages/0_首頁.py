# pages/0_首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 作業平台", page_icon="🚚", layout="wide")
inject_logistics_theme()


def _route_by_query():
    """
    用 query param 在同一視窗切頁：
    點標題 -> ?page=pages/6_出貨課首頁.py
    然後首頁收到參數後 st.switch_page() 轉頁
    """
    qp = st.query_params
    raw = qp.get("page", "")

    if isinstance(raw, list):
        raw = raw[0] if raw else ""

    if not raw:
        return

    st.query_params.clear()
    target = unquote(raw)
    st.switch_page(target)


def _home_css_and_js():
    st.markdown(
        r"""
<style>
/* =========================
   ✅ 去除藍色底 / 藍色框（首頁覆蓋）
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
   首頁清單：緊湊版（• + icon + 可點標題 + 同行描述）
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
/* ✅ 強制「同一視窗」導頁：攔截 .home-link 點擊，用 location.assign */
(function () {
  function bind() {
    document.querySelectorAll('a.home-link').forEach(a => {
      a.addEventListener('click', (e) => {
        e.preventDefault();
        const href = a.getAttribute('href');
        // 同一視窗跳轉
        window.location.assign(href);
      }, { passive: false });
    });
  }

  // 初次與每次 Streamlit 重新渲染後都再綁一次
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
    <!-- ✅ target=_self 強制同分頁（再加 JS 保險） -->
    <a class="home-link" href="?page={encoded}" target="_self">{title}：</a>
    <span class="home-desc">{desc}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def main():
    _route_by_query()

    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    # ✅ 首頁只保留「出貨課 / 進貨課」兩個入口
    card_open("📌 課別入口")
    _home_css_and_js()

    st.markdown('<div class="home-list">', unsafe_allow_html=True)

    _nav_item(
        "📦",
        "出貨課",
        "pages/7_出貨課首頁.py",
        "Outbound：撥貨差異、出貨/包裝/異常（由課別首頁統一入口）",
    )

    _nav_item(
        "🚚",
        "進貨課",
        "pages/8_進貨課首頁.py",
        "Inbound：驗收/上架/總揀/儲位/差異代庫存（由課別首頁統一入口）",
    )

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()


if __name__ == "__main__":
    main()
