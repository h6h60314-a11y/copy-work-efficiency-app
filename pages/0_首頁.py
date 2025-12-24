# pages/0_首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 作業平台", page_icon="🚚", layout="wide")
inject_logistics_theme()


def _route_by_query():
    """
    用 query param 在同一視窗切頁：
    點入口卡片 -> ?page=pages/6_出貨課首頁.py
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
   ✅ 課別入口：方框卡片（不要整個橫幅）
   ========================= */
.entry-grid{
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 360px));
  gap: 14px;
  align-items: stretch;
  justify-content: start;
  margin-top: 6px;
}
@media (max-width: 860px){
  .entry-grid{ grid-template-columns: repeat(1, minmax(260px, 1fr)); }
}

.entry-card{
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: rgba(255,255,255,0.96);
  border-radius: 14px;
  padding: 16px 16px 14px;
  min-height: 150px;
  box-shadow: 0 10px 24px rgba(2,6,23,0.06);
  transition: transform .08s ease, box-shadow .12s ease, border-color .12s ease;
  position: relative;
  overflow: hidden;
}
.entry-card:hover{
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(2,6,23,0.10);
  border-color: rgba(15, 23, 42, 0.18);
}

.entry-top{
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.entry-icon{
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: rgba(59,130,246,0.10);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 44px;
  font-size: 20px;
}
.entry-title{
  font-size: 18px;
  font-weight: 950;
  line-height: 1.2;
  color: rgba(15, 23, 42, 0.92);
  margin: 2px 0 4px;
}
.entry-sub{
  font-size: 12px;
  font-weight: 850;
  color: rgba(15, 23, 42, 0.55);
  margin: 0;
}

.entry-desc{
  margin-top: 10px;
  font-size: 13px;
  font-weight: 700;
  color: rgba(15, 23, 42, 0.72);
  line-height: 1.45;
}

.entry-cta{
  position: absolute;
  right: 14px;
  bottom: 12px;
  font-size: 13px;
  font-weight: 900;
  color: rgba(15, 23, 42, 0.70);
}
.entry-cta span{ opacity: 0.8; }

a.entry-link{
  display: block;
}

/* markdown margin reset */
div[data-testid="stMarkdown"]{ margin: 0 !important; }
</style>

<script>
/* ✅ 強制同一視窗導頁：攔截 .entry-link click */
(function () {
  function bind() {
    document.querySelectorAll('a.entry-link').forEach(a => {
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


def _entry_card(icon: str, title: str, sub: str, desc: str, page_path: str):
    encoded = quote(page_path, safe="/_.-")
    st.markdown(
        f"""
<a class="entry-link" href="?page={encoded}" target="_self">
  <div class="entry-card">
    <div class="entry-top">
      <div class="entry-icon">{icon}</div>
      <div>
        <div class="entry-title">{title}</div>
        <div class="entry-sub">{sub}</div>
      </div>
    </div>
    <div class="entry-desc">{desc}</div>
    <div class="entry-cta">進入 <span>→</span></div>
  </div>
</a>
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

    card_open("📌 課別入口")
    _home_css_and_js()

    st.markdown('<div class="entry-grid">', unsafe_allow_html=True)

    _entry_card(
        "📦",
        "出貨課",
        "Outbound",
        "撥貨差異、出貨/包裝/異常（由出貨課首頁統一入口）",
        "pages/7_出貨課首頁.py",
    )

    _entry_card(
        "🚚",
        "進貨課",
        "Inbound",
        "驗收/上架/總揀/儲位/差異代庫存（由進貨課首頁統一入口）",
        "pages/8_進貨課首頁.py",
    )

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()


if __name__ == "__main__":
    main()
