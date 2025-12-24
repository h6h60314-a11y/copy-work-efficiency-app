# pages/0_首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 作業平台", page_icon="🚚", layout="wide")
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
/* ✅ 取消連結藍底/藍框 */
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

/* ✅ 卡片外框不要藍色 */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background: rgba(255,255,255,0.98) !important;
  border-color: rgba(15, 23, 42, 0.12) !important;
  box-shadow: none !important;
}

/* =========================
   ✅ 入口卡：方框並排（像你參考圖）
   ========================= */
.entry-grid{
  display: grid;
  grid-template-columns: repeat(5, minmax(190px, 1fr));
  gap: 14px;
  align-items: stretch;
  justify-content: start;
  margin-top: 8px;
}
@media (max-width: 1280px){
  .entry-grid{ grid-template-columns: repeat(3, minmax(190px, 1fr)); }
}
@media (max-width: 900px){
  .entry-grid{ grid-template-columns: repeat(2, minmax(190px, 1fr)); }
}
@media (max-width: 640px){
  .entry-grid{ grid-template-columns: repeat(1, minmax(190px, 1fr)); }
}

.entry-tile{
  position: relative;
  border-radius: 16px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.92);
  min-height: 92px;                 /* ✅ 方框高度 */
  padding: 14px 14px 12px;
  overflow: hidden;
  box-shadow: 0 14px 26px rgba(2,6,23,0.06);
  transition: transform .08s ease, box-shadow .12s ease, border-color .12s ease;
}
.entry-tile:hover{
  transform: translateY(-1px);
  box-shadow: 0 18px 32px rgba(2,6,23,0.10);
  border-color: rgba(15,23,42,0.18);
}

/* icon + title */
.entry-title{
  display:flex;
  align-items:center;
  gap:10px;
}
.entry-ico{
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size: 18px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.85);
}
.entry-name{
  font-size: 16px;
  font-weight: 950;
  line-height: 1.15;
  color: rgba(15,23,42,0.92);
}
.entry-sub{
  margin-top: 6px;
  font-size: 12px;
  font-weight: 850;
  color: rgba(15,23,42,0.62);
  line-height: 1.35;
}

/* 右側插圖感（CSS 畫箱子） */
.illu{
  position:absolute;
  right:-18px;
  top:-22px;
  width: 140px;
  height: 140px;
  border-radius: 30px;
  transform: rotate(10deg);
  opacity: 0.92;
  pointer-events:none;
  filter: saturate(1.05);
}
.illu-out{
  background:
    radial-gradient(circle at 30% 30%, rgba(255,255,255,0.92) 0 35%, rgba(255,255,255,0) 36%),
    linear-gradient(135deg, rgba(59,130,246,0.22), rgba(37,99,235,0.10));
}
.illu-in{
  background:
    radial-gradient(circle at 30% 30%, rgba(255,255,255,0.92) 0 35%, rgba(255,255,255,0) 36%),
    linear-gradient(135deg, rgba(34,197,94,0.18), rgba(16,185,129,0.10));
}
.illu:before,.illu:after{
  content:"";
  position:absolute;
  border-radius: 10px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.75);
  box-shadow: 0 12px 20px rgba(2,6,23,0.06);
}
.illu:before{ width: 64px; height: 46px; left: 26px; top: 48px; }
.illu:after { width: 48px; height: 36px; left: 72px; top: 80px; }

.entry-cta{
  position:absolute;
  right: 12px;
  bottom: 10px;
  font-size: 12px;
  font-weight: 950;
  color: rgba(15,23,42,0.55);
}

div[data-testid="stMarkdown"]{ margin: 0 !important; }
</style>

<script>
/* ✅ 同一視窗導頁 */
(function () {
  function bind() {
    document.querySelectorAll('a[data-entry="1"]').forEach(a => {
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


def _tile_html(icon: str, title: str, sub: str, page_path: str, illu_class: str) -> str:
    encoded = quote(page_path, safe="/_.-")
    # ⚠️ 這裡刻意不做任何行首縮排，避免被 Markdown 當 code block
    return (
        f'<a data-entry="1" href="?page={encoded}" target="_self">'
        f'  <div class="entry-tile">'
        f'    <div class="entry-title">'
        f'      <div class="entry-ico">{icon}</div>'
        f'      <div class="entry-name">{title}</div>'
        f'    </div>'
        f'    <div class="entry-sub">{sub}</div>'
        f'    <div class="illu {illu_class}"></div>'
        f'    <div class="entry-cta">進入 →</div>'
        f'  </div>'
        f'</a>'
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

    tiles = [
        _tile_html("📦", "出貨課", "撥貨差異｜出貨/包裝/異常", "pages/7_出貨課首頁.py", "illu-out"),
        _tile_html("🚚", "進貨課", "驗收/上架/總揀/儲位/差異代庫存", "pages/8_進貨課首頁.py", "illu-in"),
        # 之後要加更多入口就加在這：
        # _tile_html("🧾", "盤點中心", "盤點排程｜差異彙整｜復盤", "pages/xx_盤點中心.py", "illu-out"),
    ]

    grid_html = '<div class="entry-grid">' + "".join(tiles) + "</div>"
    st.markdown(grid_html, unsafe_allow_html=True)

    card_close()


if __name__ == "__main__":
    main()
